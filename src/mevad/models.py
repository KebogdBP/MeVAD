"""Typed domain models shared by CLI and future application adapters."""

from dataclasses import dataclass
from enum import StrEnum


class SourceKind(StrEnum):
    """Supported source categories."""

    REMOTE_URL = "remote_url"
    LOCAL_FILE = "local_file"


@dataclass(frozen=True, slots=True)
class MediaSource:
    """A normalized media source accepted by the core."""

    kind: SourceKind
    value: str


class MediaAction(StrEnum):
    """Actions made available by analysis."""

    DOWNLOAD_VIDEO = "download_video"
    EXTRACT_AUDIO = "extract_audio"
    CUT_CLIP = "cut_clip"
    CREATE_GIF = "create_gif"
    DOWNLOAD_SUBTITLES = "download_subtitles"
    PROCESS_PLAYLIST = "process_playlist"


@dataclass(frozen=True, slots=True)
class MediaFormat:
    """A normalized downloadable media format."""

    format_id: str
    extension: str | None
    width: int | None
    height: int | None
    fps: float | None
    filesize_bytes: int | None
    has_video: bool
    has_audio: bool


@dataclass(frozen=True, slots=True)
class MediaAnalysis:
    """Normalized metadata returned by a media analyzer."""

    source: MediaSource
    extractor: str
    media_id: str
    title: str
    author: str | None
    duration_seconds: float | None
    thumbnail_url: str | None
    webpage_url: str
    is_playlist: bool
    playlist_entry_count: int | None
    formats: tuple[MediaFormat, ...]
    subtitle_languages: tuple[str, ...]
    available_actions: tuple[MediaAction, ...]
