"""Video downloader boundary and deterministic format planning."""

from collections.abc import Callable
from typing import Protocol, TypeAlias

from mevad.models import (
    DownloadProgress,
    VideoContainer,
    VideoDownloadRequest,
    VideoDownloadResult,
    VideoQuality,
)

ProgressCallback: TypeAlias = Callable[[DownloadProgress], None]


class CancellationToken(Protocol):
    """Read-only cancellation state supplied by a job runner."""

    @property
    def is_cancelled(self) -> bool:
        """Whether the current operation should stop."""
        ...


class VideoDownloader(Protocol):
    """Port implemented by single-video download adapters."""

    def download(
        self,
        request: VideoDownloadRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> VideoDownloadResult:
        """Download one video according to a typed request."""
        ...


def build_video_format_selector(
    quality: VideoQuality,
    container: VideoContainer,
) -> str:
    """Build a bounded yt-dlp selector from trusted enum values."""

    height = {
        VideoQuality.BEST: None,
        VideoQuality.P1080: 1080,
        VideoQuality.P720: 720,
        VideoQuality.P480: 480,
        VideoQuality.P360: 360,
    }[quality]
    video_filter = "" if height is None else f"[height<={height}]"
    if container is VideoContainer.MP4:
        return (
            f"bestvideo{video_filter}[ext=mp4]+bestaudio[ext=m4a]/"
            f"best{video_filter}[ext=mp4]/best{video_filter}"
        )
    if container is VideoContainer.WEBM:
        return (
            f"bestvideo{video_filter}[ext=webm]+bestaudio[ext=webm]/"
            f"best{video_filter}[ext=webm]/best{video_filter}"
        )
    return f"bestvideo{video_filter}+bestaudio/best{video_filter}"
