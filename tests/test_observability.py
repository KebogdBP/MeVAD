import json
import logging

from mevad_api.observability import JsonLogFormatter, MetricsRegistry


def test_json_log_formatter_emits_bounded_structured_fields() -> None:
    record = logging.LogRecord("mevad.http", logging.INFO, "", 0, "http_request", (), None)
    record.request_id = "request-123"
    record.method = "POST"
    record.path = "/api/v1/jobs"
    record.status_code = 201
    record.duration_ms = 12.5

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["event"] == "http_request"
    assert payload["request_id"] == "request-123"
    assert payload["path"] == "/api/v1/jobs"
    assert "query" not in payload


def test_metrics_registry_groups_statuses_without_high_cardinality_paths() -> None:
    registry = MetricsRegistry(clock=lambda: 100.0)
    registry.record_request("get", 200, 0.25)
    registry.record_request("GET", 204, 0.5)

    rendered = registry.render()

    assert 'mevad_http_requests_total{method="GET",status_class="2xx"} 2' in rendered
    assert (
        'mevad_http_request_duration_seconds_sum{method="GET",status_class="2xx"} 0.750000'
        in rendered
    )
