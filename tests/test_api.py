from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mevad.exceptions import InvalidSourceURLError, JobQueueError, MediaAnalysisError
from mevad.jobs import InMemoryJobQueue, InMemoryJobRepository, JobOperation, JobService
from mevad.models import (
    MediaAction,
    MediaAnalysis,
    MediaFormat,
    MediaSource,
    SourceKind,
)
from mevad.runtime import RuntimeTools
from mevad_api.abuse import AbuseProtector
from mevad_api.app import create_app
from mevad_api.config import Settings


class FakeAnalyzer:
    def __init__(
        self,
        result: MediaAnalysis | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.result = result or _analysis()
        self.error = error
        self.calls: list[MediaSource] = []

    def analyze(self, source: MediaSource) -> MediaAnalysis:
        self.calls.append(source)
        if self.error is not None:
            raise self.error
        return self.result


def test_liveness_reports_service_version() -> None:
    with _client() as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mevad-api",
        "version": "0.1.0",
    }


def test_readiness_requires_media_tools_by_default() -> None:
    with _client(runtime_tools=RuntimeTools(ffmpeg=None, ffprobe=None)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"core": True, "ffmpeg": False, "ffprobe": False},
    }


def test_readiness_can_ignore_media_tools_for_api_only_deployment() -> None:
    with _client(
        settings=_settings(require_media_tools=False),
        runtime_tools=RuntimeTools(ffmpeg=None, ffprobe=None),
    ) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_docs_can_be_disabled() -> None:
    with _client(settings=_settings(api_docs_enabled=False)) as client:
        docs_response = client.get("/docs")
        openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 404
    assert openapi_response.status_code == 404


def test_settings_reject_heartbeat_not_shorter_than_lease() -> None:
    with pytest.raises(ValidationError, match="heartbeat interval"):
        _settings(worker_lease_seconds=10, worker_heartbeat_seconds=10)


def test_settings_reject_retry_maximum_shorter_than_base() -> None:
    with pytest.raises(ValidationError, match="retry maximum"):
        _settings(worker_retry_base_seconds=10, worker_retry_max_seconds=5)


def test_settings_require_proxy_sandbox_for_enabled_analyzer() -> None:
    with pytest.raises(ValidationError, match="external proxy network sandbox"):
        _settings(analyzer_enabled=True, network_sandbox="disabled")

    with pytest.raises(ValidationError, match="media proxy URL"):
        _settings(network_sandbox="external_proxy", media_proxy_url=None)

    with pytest.raises(ValidationError, match=r"absolute HTTP\(S\) URL"):
        _settings(network_sandbox="external_proxy", media_proxy_url="socks5://proxy:1080")


def test_settings_require_long_abuse_salt_in_production() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(environment="production", abuse_protection_enabled=True, abuse_client_salt="short")


def test_analyzer_is_disabled_by_default_without_calling_adapter() -> None:
    analyzer = FakeAnalyzer()
    with _client(analyzer=analyzer) as client:
        response = client.post(
            "/api/v1/media/analyze",
            json={"url": "https://example.com/video"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "analyzer_disabled",
            "message": "Remote media analysis is disabled.",
        }
    }
    assert analyzer.calls == []


def test_analyzer_returns_normalized_response_when_enabled() -> None:
    analyzer = FakeAnalyzer()
    with _client(
        settings=_settings(analyzer_enabled=True),
        analyzer=analyzer,
    ) as client:
        response = client.post(
            "/api/v1/media/analyze",
            json={"url": "https://example.com/video"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "source_url": "https://example.com/video",
        "extractor": "Example",
        "media_id": "video-1",
        "title": "Example video",
        "author": "Creator",
        "duration_seconds": 42.5,
        "thumbnail_url": "https://cdn.example/thumbnail.jpg",
        "webpage_url": "https://example.com/video",
        "is_playlist": False,
        "playlist_entry_count": None,
        "formats": [
            {
                "format_id": "720p",
                "extension": "mp4",
                "width": 1280,
                "height": 720,
                "fps": 30.0,
                "filesize_bytes": 1000,
                "has_video": True,
                "has_audio": True,
            }
        ],
        "subtitle_languages": ["en"],
        "available_actions": ["download_video", "extract_audio"],
    }
    assert analyzer.calls == [
        MediaSource(
            kind=SourceKind.REMOTE_URL,
            value="https://example.com/video",
        )
    ]


def test_analyzer_rate_limit_returns_retry_headers() -> None:
    analyzer = FakeAnalyzer()
    settings = _settings(
        analyzer_enabled=True,
        abuse_protection_enabled=True,
        analyze_rate_limit=1,
    )
    with _client(settings=settings, analyzer=analyzer) as client:
        first = client.post("/api/v1/media/analyze", json={"url": "https://example.com/one"})
        second = client.post("/api/v1/media/analyze", json={"url": "https://example.com/two"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limit_exceeded"
    assert second.headers["retry-after"]
    assert second.headers["x-ratelimit-limit"] == "1"
    assert len(analyzer.calls) == 1


def test_analyzer_maps_invalid_url_to_stable_error() -> None:
    analyzer = FakeAnalyzer(error=InvalidSourceURLError("Only http and https URLs are allowed."))
    with _client(
        settings=_settings(analyzer_enabled=True),
        analyzer=analyzer,
    ) as client:
        response = client.post(
            "/api/v1/media/analyze",
            json={"url": "file:///etc/passwd"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_source_url"


def test_analyzer_does_not_expose_upstream_error_details() -> None:
    analyzer = FakeAnalyzer(error=MediaAnalysisError("secret upstream details"))
    with _client(
        settings=_settings(analyzer_enabled=True),
        analyzer=analyzer,
    ) as client:
        response = client.post(
            "/api/v1/media/analyze",
            json={"url": "https://example.com/video"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "media_analysis_failed",
            "message": "The media source could not be analyzed.",
        }
    }
    assert "secret" not in response.text


def test_analyzer_request_schema_rejects_empty_url() -> None:
    with _client(settings=_settings(analyzer_enabled=True)) as client:
        response = client.post("/api/v1/media/analyze", json={"url": ""})

    assert response.status_code == 422


def test_creates_reads_and_cancels_video_job() -> None:
    service = JobService(
        InMemoryJobRepository(),
        job_id_factory=lambda: "job-1",
    )
    with _client(job_service=service) as client:
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "operation": "download_video",
                "source_url": "https://EXAMPLE.com/video#fragment",
                "options": {"quality": "720p", "container": "mp4"},
            },
        )
        get_response = client.get("/api/v1/jobs/job-1")
        cancel_response = client.post("/api/v1/jobs/job-1/cancel")

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "queued"
    assert create_response.json()["source_url"] == "https://example.com/video"
    assert create_response.json()["parameters"] == {
        "quality": "720p",
        "container": "mp4",
    }
    assert create_response.json()["attempt_count"] == 0
    assert create_response.json()["max_attempts"] == 3
    assert get_response.status_code == 200
    assert get_response.json()["version"] == 1
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"
    assert cancel_response.json()["version"] == 2
    assert cancel_response.json()["result_expires_at"] is not None
    assert cancel_response.json()["storage_deleted_at"] is None


def test_active_job_quota_is_released_after_cancellation() -> None:
    job_ids = iter(["job-1", "job-2"])
    service = JobService(InMemoryJobRepository(), job_id_factory=lambda: next(job_ids))
    settings = _settings(
        abuse_protection_enabled=True,
        anonymous_active_job_limit=1,
        job_create_rate_limit=10,
    )
    payload = {
        "operation": "download_video",
        "source_url": "https://example.com/video",
        "options": {"quality": "720p", "container": "mp4"},
    }
    with _client(settings=settings, job_service=service) as client:
        first = client.post("/api/v1/jobs", json=payload)
        blocked = client.post("/api/v1/jobs", json=payload)
        cancelled = client.post("/api/v1/jobs/job-1/cancel")
        second = client.post("/api/v1/jobs", json=payload)

    assert first.status_code == 201
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "anonymous_job_limit_reached"
    assert cancelled.status_code == 200
    assert second.status_code == 201
    assert second.json()["job_id"] == "job-2"


def test_job_api_validates_discriminated_options() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/jobs",
            json={
                "operation": "make_loop",
                "source_url": "https://example.com/video",
                "options": {
                    "start_seconds": 0,
                    "end_seconds": 31,
                    "output_format": "gif",
                },
            },
        )

    assert response.status_code == 422


def test_job_api_rejects_unsafe_source_before_enqueue() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/jobs",
            json={
                "operation": "extract_audio",
                "source_url": "http://127.0.0.1/private",
                "options": {"codec": "mp3", "bitrate": "192"},
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_source_url"


def test_job_api_returns_service_unavailable_when_queue_fails() -> None:
    class FailingQueue(InMemoryJobQueue):
        def enqueue(self, job_id: str) -> None:
            raise JobQueueError("offline")

    service = JobService(
        InMemoryJobRepository(),
        queue=FailingQueue(),
        job_id_factory=lambda: "job-1",
    )
    with _client(job_service=service) as client:
        response = client.post(
            "/api/v1/jobs",
            json={
                "operation": "download_video",
                "source_url": "https://example.com/video",
                "options": {"quality": "720p", "container": "mp4"},
            },
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "job_queue_unavailable"
    assert service.get("job-1").status.value == "failed"


def test_postgres_job_creation_commits_outbox_without_redis(
    tmp_path: Path,
) -> None:
    settings = _settings(
        job_backend="postgres",
        queue_backend="redis",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}",
        redis_url="redis://127.0.0.1:1/0",
        auto_create_schema=True,
    )

    with _client(settings=settings) as client:
        response = client.post(
            "/api/v1/jobs",
            json={
                "operation": "download_video",
                "source_url": "https://example.com/video",
                "options": {"quality": "720p", "container": "mp4"},
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_job_api_returns_stable_not_found_error() -> None:
    with _client() as client:
        get_response = client.get("/api/v1/jobs/missing")
        cancel_response = client.post("/api/v1/jobs/missing/cancel")

    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "job_not_found"
    assert cancel_response.status_code == 404


def test_job_api_rejects_cancelling_terminal_job() -> None:
    service = JobService(
        InMemoryJobRepository(),
        job_id_factory=lambda: "job-1",
    )
    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    service.cancel("job-1")

    with _client(job_service=service) as client:
        response = client.post("/api/v1/jobs/job-1/cancel")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "job_not_cancellable"


def test_job_result_streams_completed_file_with_download_headers(tmp_path: Path) -> None:
    service = JobService(InMemoryJobRepository(), job_id_factory=lambda: "job-1")
    job = service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    service.start(job.job_id)
    result = tmp_path / "job-1" / "results" / "Example video.mp4"
    result.parent.mkdir(parents=True)
    result.write_bytes(b"video")
    service.succeed(job.job_id, result_reference="job-1/results/Example video.mp4")

    with _client(settings=_settings(storage_root=tmp_path), job_service=service) as client:
        response = client.get("/api/v1/jobs/job-1/result")

    assert response.status_code == 200
    assert response.content == b"video"
    assert response.headers["content-disposition"].startswith("attachment; filename")
    assert "Example%20video.mp4" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_job_result_is_not_available_before_success(tmp_path: Path) -> None:
    service = JobService(InMemoryJobRepository(), job_id_factory=lambda: "job-1")
    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )

    with _client(settings=_settings(storage_root=tmp_path), job_service=service) as client:
        response = client.get("/api/v1/jobs/job-1/result")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "job_result_not_ready"


def test_job_result_rejects_reference_outside_owning_workspace(tmp_path: Path) -> None:
    service = JobService(InMemoryJobRepository(), job_id_factory=lambda: "job-1")
    job = service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    service.start(job.job_id)
    other = tmp_path / "job-2" / "results" / "private.mp4"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"private")
    service.succeed(job.job_id, result_reference="job-2/results/private.mp4")

    with _client(settings=_settings(storage_root=tmp_path), job_service=service) as client:
        response = client.get("/api/v1/jobs/job-1/result")

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "job_result_unavailable"
    assert b"private" not in response.content


@contextmanager
def _client(
    *,
    settings: Settings | None = None,
    analyzer: FakeAnalyzer | None = None,
    runtime_tools: RuntimeTools | None = None,
    job_service: JobService | None = None,
    abuse_protector: AbuseProtector | None = None,
) -> Iterator[TestClient]:
    app = create_app(
        settings=settings or _settings(),
        analyzer=analyzer or FakeAnalyzer(),
        runtime_tools=runtime_tools or RuntimeTools(ffmpeg="/bin/ffmpeg", ffprobe="/bin/ffprobe"),
        job_service=job_service,
        abuse_protector=abuse_protector,
    )
    with TestClient(app) as client:
        yield client


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {"environment": "test", **overrides}
    if values.get("analyzer_enabled") is True:
        values.setdefault("network_sandbox", "external_proxy")
        values.setdefault("media_proxy_url", "http://egress-proxy:3128")
    return Settings.model_validate(values)


def _analysis() -> MediaAnalysis:
    return MediaAnalysis(
        source=MediaSource(
            kind=SourceKind.REMOTE_URL,
            value="https://example.com/video",
        ),
        extractor="Example",
        media_id="video-1",
        title="Example video",
        author="Creator",
        duration_seconds=42.5,
        thumbnail_url="https://cdn.example/thumbnail.jpg",
        webpage_url="https://example.com/video",
        is_playlist=False,
        playlist_entry_count=None,
        formats=(
            MediaFormat(
                format_id="720p",
                extension="mp4",
                width=1280,
                height=720,
                fps=30.0,
                filesize_bytes=1000,
                has_video=True,
                has_audio=True,
            ),
        ),
        subtitle_languages=("en",),
        available_actions=(
            MediaAction.DOWNLOAD_VIDEO,
            MediaAction.EXTRACT_AUDIO,
        ),
    )
