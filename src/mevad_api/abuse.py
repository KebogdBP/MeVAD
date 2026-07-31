"""Public API abuse controls shared by HTTP routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from hmac import new as new_hmac
from ipaddress import ip_address
from math import ceil
from threading import Lock
from time import time
from typing import Protocol, cast
from uuid import uuid4

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from mevad_api.config import Settings


class AbuseProtectionError(RuntimeError):
    """Raised when protection state cannot be read or updated safely."""


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class AbuseProtector(Protocol):
    def check_rate(
        self, client_key: str, action: str, *, limit: int, window: int
    ) -> RateLimitResult: ...

    def reserve_job(self, client_key: str, *, limit: int, ttl: int) -> str | None: ...

    def bind_job(self, reservation: str, job_id: str, *, ttl: int) -> None: ...

    def release_reservation(self, reservation: str) -> None: ...

    def release_job(self, job_id: str) -> None: ...

    def close(self) -> None: ...


class NoopAbuseProtector:
    def check_rate(
        self, client_key: str, action: str, *, limit: int, window: int
    ) -> RateLimitResult:
        return RateLimitResult(True, limit, limit, 0)

    def reserve_job(self, client_key: str, *, limit: int, ttl: int) -> str | None:
        return uuid4().hex

    def bind_job(self, reservation: str, job_id: str, *, ttl: int) -> None:
        return None

    def release_reservation(self, reservation: str) -> None:
        return None

    def release_job(self, job_id: str) -> None:
        return None

    def close(self) -> None:
        return None


class InMemoryAbuseProtector:
    """Process-local implementation for development and deterministic tests."""

    def __init__(self, *, clock: Callable[[], float] = time) -> None:
        self._clock = clock
        self._rates: dict[tuple[str, str, int], int] = {}
        self._reservations: dict[str, tuple[str, float]] = {}
        self._jobs: dict[str, str] = {}
        self._lock = Lock()

    def check_rate(
        self, client_key: str, action: str, *, limit: int, window: int
    ) -> RateLimitResult:
        now = self._clock()
        bucket = int(now // window)
        key = (client_key, action, bucket)
        retry_after = max(1, ceil((bucket + 1) * window - now))
        with self._lock:
            stale = [rate_key for rate_key in self._rates if rate_key[2] < bucket - 1]
            for rate_key in stale:
                self._rates.pop(rate_key, None)
            count = self._rates.get(key, 0) + 1
            self._rates[key] = count
        return RateLimitResult(count <= limit, limit, max(0, limit - count), retry_after)

    def reserve_job(self, client_key: str, *, limit: int, ttl: int) -> str | None:
        now = self._clock()
        with self._lock:
            expired = [
                token for token, (_, expires) in self._reservations.items() if expires <= now
            ]
            for token in expired:
                self._reservations.pop(token, None)
                self._jobs = {job: value for job, value in self._jobs.items() if value != token}
            active = sum(owner == client_key for owner, _ in self._reservations.values())
            if active >= limit:
                return None
            token = uuid4().hex
            self._reservations[token] = (client_key, now + ttl)
            return token

    def bind_job(self, reservation: str, job_id: str, *, ttl: int) -> None:
        with self._lock:
            if reservation in self._reservations:
                self._jobs[job_id] = reservation

    def release_reservation(self, reservation: str) -> None:
        with self._lock:
            self._reservations.pop(reservation, None)
            self._jobs = {job: value for job, value in self._jobs.items() if value != reservation}

    def release_job(self, job_id: str) -> None:
        with self._lock:
            reservation = self._jobs.pop(job_id, None)
            if reservation is not None:
                self._reservations.pop(reservation, None)

    def close(self) -> None:
        return None


class RedisEvalClient(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> object: ...
    def close(self) -> object: ...


_RATE_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""

_RESERVE_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
redis.call('ZADD', KEYS[1], ARGV[3], ARGV[4])
redis.call('SET', KEYS[2], KEYS[1], 'EX', ARGV[5])
return 1
"""

_BIND_SCRIPT = """
local owner = redis.call('GET', KEYS[1])
if not owner then return 0 end
redis.call('SET', KEYS[2], owner .. '|' .. ARGV[1], 'EX', ARGV[2])
return 1
"""

_RELEASE_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if not value then return 0 end
local divider = string.find(value, '|', 1, true)
local owner = value
local token = ARGV[1]
if divider then
  owner = string.sub(value, 1, divider - 1)
  token = string.sub(value, divider + 1)
end
redis.call('ZREM', owner, token)
redis.call('DEL', KEYS[1])
return 1
"""


class RedisAbuseProtector:
    """Atomic distributed controls for multi-process production deployments."""

    def __init__(self, client: RedisEvalClient, *, clock: Callable[[], float] = time) -> None:
        self._client = client
        self._clock = clock

    @classmethod
    def from_url(cls, redis_url: str) -> RedisAbuseProtector:
        return cls(cast(RedisEvalClient, Redis.from_url(redis_url, decode_responses=False)))

    def check_rate(
        self, client_key: str, action: str, *, limit: int, window: int
    ) -> RateLimitResult:
        bucket = int(self._clock() // window)
        key = f"mevad:abuse:rate:{action}:{client_key}:{bucket}"
        try:
            raw = self._client.eval(_RATE_SCRIPT, 1, key, str(window + 1))
            count, ttl = cast(list[int], raw)
        except (RedisError, TypeError, ValueError) as error:
            raise AbuseProtectionError("Rate limit state is unavailable.") from error
        return RateLimitResult(count <= limit, limit, max(0, limit - count), max(1, ttl))

    def reserve_job(self, client_key: str, *, limit: int, ttl: int) -> str | None:
        token = uuid4().hex
        owner = f"mevad:abuse:active:{client_key}"
        reservation = f"mevad:abuse:reservation:{token}"
        try:
            allowed = self._client.eval(
                _RESERVE_SCRIPT,
                2,
                owner,
                reservation,
                str(self._clock()),
                str(limit),
                str(self._clock() + ttl),
                token,
                str(ttl),
            )
        except RedisError as error:
            raise AbuseProtectionError("Active job quota is unavailable.") from error
        return token if allowed == 1 else None

    def bind_job(self, reservation: str, job_id: str, *, ttl: int) -> None:
        try:
            self._client.eval(
                _BIND_SCRIPT,
                2,
                f"mevad:abuse:reservation:{reservation}",
                f"mevad:abuse:job:{job_id}",
                reservation,
                str(ttl),
            )
        except RedisError as error:
            raise AbuseProtectionError("Job quota state could not be bound.") from error

    def release_reservation(self, reservation: str) -> None:
        self._release(f"mevad:abuse:reservation:{reservation}", reservation)

    def release_job(self, job_id: str) -> None:
        self._release(f"mevad:abuse:job:{job_id}", "")

    def _release(self, key: str, token: str) -> None:
        try:
            self._client.eval(_RELEASE_SCRIPT, 1, key, token)
        except RedisError as error:
            raise AbuseProtectionError("Job quota state could not be released.") from error

    def close(self) -> None:
        self._client.close()


def client_key(request: Request, settings: Settings) -> str:
    """Return a non-reversible stable client identifier without retaining an IP."""

    candidate = request.client.host if request.client is not None else "unknown"
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", maxsplit=1)[0].strip()
        with suppress(ValueError):
            candidate = str(ip_address(forwarded))
    digest = new_hmac(settings.abuse_client_salt.encode("utf-8"), candidate.encode("utf-8"), sha256)
    return digest.hexdigest()


def create_abuse_protector(settings: Settings) -> AbuseProtector:
    if not settings.abuse_protection_enabled:
        return NoopAbuseProtector()
    if settings.abuse_backend == "redis":
        return RedisAbuseProtector.from_url(settings.redis_url)
    return InMemoryAbuseProtector()
