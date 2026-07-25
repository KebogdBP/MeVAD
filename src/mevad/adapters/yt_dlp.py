"""yt-dlp metadata analyzer adapter."""

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from typing import Any, Protocol, TypeAlias, cast

from mevad.exceptions import MediaAnalysisError, UnsupportedMediaError
from mevad.models import (
    MediaAction,
    MediaAnalysis,
    MediaFormat,
    MediaSource,
    SourceKind,
)
from mevad.security import normalize_remote_url

Info: TypeAlias = Mapping[str, Any]


class YoutubeDLClient(Protocol):
    """Small subset of YoutubeDL used by this adapter."""

    def extract_info(self, url: str, *, download: bool) -> Info | None:
        """Extract metadata for a URL."""
        ...

    def sanitize_info(self, info_dict: Info) -> Info:
        """Return metadata containing JSON-compatible public values."""
        ...


ClientContext: TypeAlias = AbstractContextManager[YoutubeDLClient]
ClientFactory: TypeAlias = Callable[[Mapping[str, Any]], ClientContext]


class YtDlpAnalyzer:
    """Analyze remote media through yt-dlp without downloading the payload."""

    def __init__(
        self,
        client_factory: ClientFactory | None = None,
        *,
        proxy_url: str | None = None,
    ) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._proxy_url = proxy_url

    def analyze(self, source: MediaSource) -> MediaAnalysis:
        if source.kind is not SourceKind.REMOTE_URL:
            raise UnsupportedMediaError("yt-dlp analyzer accepts remote URLs only.")

        normalized_url = normalize_remote_url(source.value)
        options: Mapping[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "playlistend": 100,
            "socket_timeout": 15,
            "retries": 1,
            "extractor_retries": 1,
            "ignoreconfig": True,
            "usenetrc": False,
            **({"proxy": self._proxy_url} if self._proxy_url is not None else {}),
        }

        try:
            with self._client_factory(options) as client:
                extracted = client.extract_info(normalized_url, download=False)
                if extracted is None:
                    raise MediaAnalysisError("yt-dlp returned no metadata.")
                info = client.sanitize_info(extracted)
        except MediaAnalysisError:
            raise
        except Exception as error:
            raise MediaAnalysisError(_safe_error_message(error)) from error

        return _normalize_analysis(source, normalized_url, info)


def _default_client_factory(options: Mapping[str, Any]) -> ClientContext:
    import yt_dlp  # type: ignore[import-untyped]

    return cast(ClientContext, yt_dlp.YoutubeDL(dict(options)))


def _normalize_analysis(
    source: MediaSource,
    normalized_url: str,
    info: Info,
) -> MediaAnalysis:
    media_id = _required_text(info, "id")
    title = _required_text(info, "title")
    is_playlist = info.get("_type") in {"playlist", "multi_video"}
    formats = () if is_playlist else _normalize_formats(info.get("formats"))
    subtitles = _normalize_subtitle_languages(info)
    actions = _available_actions(
        formats=formats,
        subtitles=subtitles,
        is_playlist=is_playlist,
    )

    return MediaAnalysis(
        source=MediaSource(kind=source.kind, value=normalized_url),
        extractor=_optional_text(info.get("extractor_key"))
        or _optional_text(info.get("extractor"))
        or "unknown",
        media_id=media_id,
        title=title,
        author=_optional_text(info.get("uploader")) or _optional_text(info.get("channel")),
        duration_seconds=_optional_number(info.get("duration")),
        thumbnail_url=_optional_text(info.get("thumbnail")),
        webpage_url=_optional_text(info.get("webpage_url")) or normalized_url,
        is_playlist=is_playlist,
        playlist_entry_count=_playlist_entry_count(info) if is_playlist else None,
        formats=formats,
        subtitle_languages=subtitles,
        available_actions=actions,
    )


def _normalize_formats(raw_formats: object) -> tuple[MediaFormat, ...]:
    if not isinstance(raw_formats, list):
        return ()

    formats: list[MediaFormat] = []
    for raw_format in raw_formats:
        if not isinstance(raw_format, Mapping):
            continue
        format_id = _optional_text(raw_format.get("format_id"))
        if format_id is None:
            continue
        video_codec = _optional_text(raw_format.get("vcodec"))
        audio_codec = _optional_text(raw_format.get("acodec"))
        formats.append(
            MediaFormat(
                format_id=format_id,
                extension=_optional_text(raw_format.get("ext")),
                width=_optional_integer(raw_format.get("width")),
                height=_optional_integer(raw_format.get("height")),
                fps=_optional_number(raw_format.get("fps")),
                filesize_bytes=_optional_integer(
                    raw_format.get("filesize") or raw_format.get("filesize_approx")
                ),
                has_video=video_codec not in {None, "none"},
                has_audio=audio_codec not in {None, "none"},
            )
        )
    return tuple(formats)


def _normalize_subtitle_languages(info: Info) -> tuple[str, ...]:
    languages: set[str] = set()
    for key in ("subtitles", "automatic_captions"):
        tracks = info.get(key)
        if isinstance(tracks, Mapping):
            languages.update(str(language) for language in tracks)
    return tuple(sorted(languages))


def _available_actions(
    *,
    formats: tuple[MediaFormat, ...],
    subtitles: tuple[str, ...],
    is_playlist: bool,
) -> tuple[MediaAction, ...]:
    if is_playlist:
        return (MediaAction.PROCESS_PLAYLIST,)

    actions: list[MediaAction] = []
    if any(media_format.has_video for media_format in formats):
        actions.extend(
            [
                MediaAction.DOWNLOAD_VIDEO,
                MediaAction.CUT_CLIP,
                MediaAction.CREATE_GIF,
            ]
        )
    if any(media_format.has_audio for media_format in formats):
        actions.append(MediaAction.EXTRACT_AUDIO)
    if subtitles:
        actions.append(MediaAction.DOWNLOAD_SUBTITLES)
    return tuple(actions)


def _playlist_entry_count(info: Info) -> int | None:
    declared_count = _optional_integer(info.get("playlist_count"))
    if declared_count is not None:
        return declared_count
    entries = info.get("entries")
    return len(entries) if isinstance(entries, list) else None


def _required_text(info: Info, key: str) -> str:
    value = _optional_text(info.get(key))
    if value is None:
        raise UnsupportedMediaError(f"Extracted metadata has no {key}.")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _optional_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _safe_error_message(error: Exception) -> str:
    message = str(error).strip()
    return f"Media analysis failed: {message or type(error).__name__}"
