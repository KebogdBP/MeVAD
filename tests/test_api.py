from collections.abc import Iterator
from contextlib import contextmanager

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


@contextmanager
def _client(
    *,
    settings: Settings | None = None,
    analyzer: FakeAnalyzer | None = None,
    runtime_tools: RuntimeTools | None = None,
    job_service: JobService | None = None,
) -> Iterator[TestClient]:
    app = create_app(
        settings=settings or _settings(),
        analyzer=analyzer or FakeAnalyzer(),
        runtime_tools=runtime_tools or RuntimeTools(ffmpeg="/bin/ffmpeg", ffprobe="/bin/ffprobe"),
        job_service=job_service,
    )
    with TestClient(app) as client:
        yield client


def _settings(**overrides: object) -> Settings:
    return Settings.model_validate({"environment": "test", **overrides})


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
