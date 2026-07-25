import pytest

from mevad.downloader import build_video_format_selector
from mevad.models import DownloadProgress, DownloadStatus, VideoContainer, VideoQuality


@pytest.mark.parametrize(
    ("quality", "container", "expected"),
    [
        (
            VideoQuality.BEST,
            VideoContainer.AUTO,
            "bestvideo+bestaudio/best",
        ),
        (
            VideoQuality.P720,
            VideoContainer.AUTO,
            "bestvideo[height<=720]+bestaudio/best[height<=720]",
        ),
        (
            VideoQuality.P1080,
            VideoContainer.MP4,
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
            "best[height<=1080][ext=mp4]/best[height<=1080]",
        ),
        (
            VideoQuality.P480,
            VideoContainer.WEBM,
            "bestvideo[height<=480][ext=webm]+bestaudio[ext=webm]/"
            "best[height<=480][ext=webm]/best[height<=480]",
        ),
        (
            VideoQuality.P360,
            VideoContainer.MKV,
            "bestvideo[height<=360]+bestaudio/best[height<=360]",
        ),
    ],
)
def test_builds_bounded_format_selector(
    quality: VideoQuality,
    container: VideoContainer,
    expected: str,
) -> None:
    assert build_video_format_selector(quality, container) == expected


def test_progress_fraction_is_bounded() -> None:
    progress = DownloadProgress(
        status=DownloadStatus.DOWNLOADING,
        downloaded_bytes=120,
        total_bytes=100,
    )

    assert progress.fraction == 1.0


def test_progress_fraction_is_unknown_without_total() -> None:
    progress = DownloadProgress(
        status=DownloadStatus.DOWNLOADING,
        downloaded_bytes=10,
    )

    assert progress.fraction is None
