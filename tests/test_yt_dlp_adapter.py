from collections.abc import Mapping
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any

import pytest

from mevad.adapters.yt_dlp import YoutubeDLClient, YtDlpAnalyzer
from mevad.exceptions import MediaAnalysisError, UnsupportedMediaError
from mevad.models import MediaAction, MediaSource, SourceKind


class FakeYoutubeDL(AbstractContextManager[YoutubeDLClient]):
    def __init__(
        self,
        info: Mapping[str, Any] | None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.info = info
        self.error = error
        self.requested_url: str | None = None
        self.download: bool | None = None

    def __enter__(self) -> YoutubeDLClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def extract_info(self, url: str, *, download: bool) -> Mapping[str, Any] | None:
        self.requested_url = url
        self.download = download
        if self.error is not None:
            raise self.error
        return self.info

    def sanitize_info(self, info_dict: Mapping[str, Any]) -> Mapping[str, Any]:
        return info_dict


def test_analyzes_video_without_downloading() -> None:
    client = FakeYoutubeDL(
        {
            "id": "video-1",
            "title": "Example",
            "extractor_key": "Example",
            "uploader": "Creator",
            "duration": 12.5,
            "thumbnail": "https://cdn.example/thumbnail.jpg",
            "webpage_url": "https://example.com/watch/1",
            "formats": [
                {
                    "format_id": "video",
                    "ext": "mp4",
                    "width": 1920,
                    "height": 1080,
                    "fps": 30,
                    "filesize": 1000,
                    "vcodec": "avc1",
                    "acodec": "none",
                },
                {
                    "format_id": "audio",
                    "ext": "m4a",
                    "filesize_approx": 200,
                    "vcodec": "none",
                    "acodec": "mp4a",
                },
            ],
            "subtitles": {"en": [{"ext": "vtt"}]},
            "automatic_captions": {"ru": [{"ext": "vtt"}]},
        }
    )
    analyzer = YtDlpAnalyzer(client_factory=lambda _options: client)

    result = analyzer.analyze(
        MediaSource(kind=SourceKind.REMOTE_URL, value="https://EXAMPLE.com/watch/1#part")
    )

    assert client.requested_url == "https://example.com/watch/1"
    assert client.download is False
    assert result.media_id == "video-1"
    assert result.title == "Example"
    assert result.duration_seconds == 12.5
    assert result.subtitle_languages == ("en", "ru")
    assert len(result.formats) == 2
    assert result.formats[0].height == 1080
    assert result.formats[1].filesize_bytes == 200
    assert result.available_actions == (
        MediaAction.DOWNLOAD_VIDEO,
        MediaAction.CUT_CLIP,
        MediaAction.CREATE_GIF,
        MediaAction.EXTRACT_AUDIO,
        MediaAction.DOWNLOAD_SUBTITLES,
    )


def test_analyzes_playlist_as_workspace_action() -> None:
    client = FakeYoutubeDL(
        {
            "_type": "playlist",
            "id": "playlist-1",
            "title": "Course",
            "extractor": "example:playlist",
            "entries": [{"id": "1"}, {"id": "2"}],
        }
    )
    analyzer = YtDlpAnalyzer(client_factory=lambda _options: client)

    result = analyzer.analyze(
        MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/playlist/1")
    )

    assert result.is_playlist
    assert result.playlist_entry_count == 2
    assert result.formats == ()
    assert result.available_actions == (MediaAction.PROCESS_PLAYLIST,)


def test_analyzer_forces_proxy_and_ignores_user_configuration() -> None:
    client = FakeYoutubeDL({"id": "video-1", "title": "Example", "formats": []})
    captured: dict[str, Any] = {}

    def factory(options: Mapping[str, Any]) -> FakeYoutubeDL:
        captured.update(options)
        return client

    analyzer = YtDlpAnalyzer(
        client_factory=factory,
        proxy_url="http://egress-proxy:3128",
    )
    analyzer.analyze(MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/video"))

    assert captured["proxy"] == "http://egress-proxy:3128"
    assert captured["ignoreconfig"] is True
    assert captured["usenetrc"] is False


def test_rejects_local_file_source() -> None:
    analyzer = YtDlpAnalyzer(client_factory=lambda _options: FakeYoutubeDL({}))

    with pytest.raises(UnsupportedMediaError, match="remote URLs only"):
        analyzer.analyze(MediaSource(kind=SourceKind.LOCAL_FILE, value="/tmp/video.mp4"))


def test_converts_external_failure_to_domain_error() -> None:
    analyzer = YtDlpAnalyzer(
        client_factory=lambda _options: FakeYoutubeDL(None, error=RuntimeError("upstream failed"))
    )

    with pytest.raises(MediaAnalysisError, match="upstream failed"):
        analyzer.analyze(MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/video"))


def test_rejects_incomplete_metadata() -> None:
    analyzer = YtDlpAnalyzer(client_factory=lambda _options: FakeYoutubeDL({"id": "video-1"}))

    with pytest.raises(UnsupportedMediaError, match="no title"):
        analyzer.analyze(MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/video"))
