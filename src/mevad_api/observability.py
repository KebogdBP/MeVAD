"""Privacy-safe API logging, request correlation and runtime metrics."""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable
from threading import Lock
from time import gmtime, monotonic, time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")
_HTTP_LOGGER = logging.getLogger("mevad.http")


class JsonLogFormatter(logging.Formatter):
    """Emit one bounded JSON object per API access event."""

    converter = staticmethod(lambda timestamp=None: gmtime(timestamp))

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        for name in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, name, None)
            if value is not None:
                payload[name] = value
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


class MetricsRegistry:
    """Small process-local registry suitable for an internal Prometheus scrape."""

    def __init__(self, *, clock: Callable[[], float] = time) -> None:
        self._started_at = clock()
        self._requests: Counter[tuple[str, str]] = Counter()
        self._duration_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._lock = Lock()

    def record_request(self, method: str, status_code: int, duration_seconds: float) -> None:
        status_class = f"{status_code // 100}xx"
        key = (method.upper(), status_class)
        with self._lock:
            self._requests[key] += 1
            self._duration_sum[key] += duration_seconds

    def render(self) -> str:
        lines = [
            "# HELP mevad_process_start_time_seconds Process start time as a Unix timestamp.",
            "# TYPE mevad_process_start_time_seconds gauge",
            f"mevad_process_start_time_seconds {self._started_at:.3f}",
            "# HELP mevad_http_requests_total HTTP requests handled by this API process.",
            "# TYPE mevad_http_requests_total counter",
            "# HELP mevad_http_request_duration_seconds "
            "Request duration by method and status class.",
            "# TYPE mevad_http_request_duration_seconds summary",
        ]
        with self._lock:
            keys = sorted(self._requests)
            for method, status_class in keys:
                labels = f'method="{method}",status_class="{status_class}"'
                count = self._requests[(method, status_class)]
                duration = self._duration_sum[(method, status_class)]
                lines.append(f"mevad_http_requests_total{{{labels}}} {count}")
                lines.append(f"mevad_http_request_duration_seconds_sum{{{labels}}} {duration:.6f}")
                lines.append(f"mevad_http_request_duration_seconds_count{{{labels}}} {count}")
        return "\n".join(lines) + "\n"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and record privacy-safe request outcome signals."""

    def __init__(self, app: ASGIApp, *, metrics: MetricsRegistry) -> None:
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _request_id(request.headers.get("x-request-id"))
        started = monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = monotonic() - started
            self._metrics.record_request(request.method, status_code, duration)
            _HTTP_LOGGER.info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )


def configure_http_logging(*, level: str, json_output: bool) -> None:
    """Configure the dedicated access logger without mutating application loggers."""

    handler = logging.StreamHandler()
    if json_output:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s "
                "request_id=%(request_id)s method=%(method)s path=%(path)s "
                "status=%(status_code)s duration_ms=%(duration_ms)s"
            )
        )
    _HTTP_LOGGER.handlers.clear()
    _HTTP_LOGGER.addHandler(handler)
    _HTTP_LOGGER.setLevel(level)
    _HTTP_LOGGER.propagate = False


def _request_id(candidate: str | None) -> str:
    if candidate is not None and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex
