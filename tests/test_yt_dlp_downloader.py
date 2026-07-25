from collections.abc import Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

from mevad.adapters.yt_dlp_downloader import DownloadClient, YtDlpVideoDownloader
from mevad.exceptions import DownloadCancelledError, MediaDownloadError, UnsupportedMediaError
from mevad.models import (
    DownloadProgress,
    DownloadStatus,
    MediaSource,
    SourceKind,
    VideoContainer,
    VideoDownloadRequest,
    VideoQuality,
)


class FakeDownloadClient(AbstractContextManager[DownloadClient]):
    def __init__(
        self,
        options: Mapping[str, Any],
        output_path: Path,
        *,
        error: Exception | None = None,
    ) -> None:
        self.options = options
        self.output_path = output_path
        self.error = error
        self.requested_url: str | None = None
        self.download: bool | None = None

    def __enter__(self) -> DownloadClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def extract_info(self, url: str, *, download: bool) -> Mapping[str, Any] | None:
        if self.error is not None:
            raise self.error
        self.requested_url = url
        self.download = download
        self.output_path.write_bytes(b"video-data")

        progress_hook = self.options["progress_hooks"][0]
        progress_hook(
            {
                "status": "downloading",
                "downloaded_bytes": 5,
                "total_bytes": 10,
                "speed": 2.5,
                "eta": 2,
                "filename": str(self.output_path.with_suffix(".part")),
            }
        )
        progress_hook(
            {
                "status": "finished",
                "downloaded_bytes": 10,
                "total_bytes": 10,
                "filename": str(self.output_path),
            }
        )
        postprocessor_hook = self.options["postprocessor_hooks"][0]
        postprocessor_hook(
            {
                "status": "finished",
                "info_dict": {"filepath": str(self.output_path)},
            }
        )
        return {
            "id": "video-1",
            "title": "Example video",
            "filepath": str(self.output_path),
        }


class Token:
    def __init__(self, is_cancelled: bool = False) -> None:
        self.is_cancelled = is_cancelled


def test_downloads_video_and_emits_normalized_progress(tmp_path: Path) -> None:
    output_path = tmp_path / "Example [video-1].mp4"
    captured_options: Mapping[str, Any] | None = None

    def factory(options: Mapping[str, Any]) -> FakeDownloadClient:
        nonlocal captured_options
        captured_options = options
        return FakeDownloadClient(options, output_path)

    events: list[DownloadProgress] = []
    downloader = YtDlpVideoDownloader(client_factory=factory)

    result = downloader.download(
        VideoDownloadRequest(
            source=MediaSource(
                kind=SourceKind.REMOTE_URL,
                value="https://EXAMPLE.com/video#fragment",
            ),
            output_directory=tmp_path,
            quality=VideoQuality.P720,
            container=VideoContainer.MP4,
        ),
        on_progress=events.append,
    )

    assert result.media_id == "video-1"
    assert result.output_path == output_path
    assert result.filesize_bytes == len(b"video-data")
    assert [event.status for event in events] == [
        DownloadStatus.DOWNLOADING,
        DownloadStatus.PROCESSING,
        DownloadStatus.PROCESSING,
        DownloadStatus.COMPLETED,
    ]
    assert events[0].fraction == 0.5
    assert captured_options is not None
    assert captured_options["noplaylist"] is True
    assert captured_options["merge_output_format"] == "mp4"
    assert captured_options["paths"] == {"home": str(tmp_path)}


def test_rejects_path_outside_output_directory(tmp_path: Path) -> None:
    outside_path = tmp_path.parent / "outside.mp4"
    downloader = YtDlpVideoDownloader(
        client_factory=lambda options: FakeDownloadClient(options, outside_path)
    )

    with pytest.raises(MediaDownloadError, match="outside the output directory"):
        downloader.download(_request(tmp_path))


def test_rejects_local_file_source(tmp_path: Path) -> None:
    downloader = YtDlpVideoDownloader()
    request = VideoDownloadRequest(
        source=MediaSource(kind=SourceKind.LOCAL_FILE, value="/tmp/video.mp4"),
        output_directory=tmp_path,
    )

    with pytest.raises(UnsupportedMediaError, match="remote URLs only"):
        downloader.download(request)


def test_honors_pre_cancelled_token(tmp_path: Path) -> None:
    downloader = YtDlpVideoDownloader()

    with pytest.raises(DownloadCancelledError):
        downloader.download(_request(tmp_path), cancellation=Token(is_cancelled=True))


def test_converts_external_error_to_domain_error(tmp_path: Path) -> None:
    output_path = tmp_path / "video.mp4"
    downloader = YtDlpVideoDownloader(
        client_factory=lambda options: FakeDownloadClient(
            options,
            output_path,
            error=RuntimeError("upstream failed"),
        )
    )

    with pytest.raises(MediaDownloadError, match="upstream failed"):
        downloader.download(_request(tmp_path))


def _request(output_directory: Path) -> VideoDownloadRequest:
    return VideoDownloadRequest(
        source=MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/video"),
        output_directory=output_directory,
    )
