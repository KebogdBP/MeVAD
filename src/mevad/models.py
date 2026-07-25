"""Typed domain models shared by CLI and future application adapters."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


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


class VideoQuality(StrEnum):
    """User-facing video quality presets."""

    BEST = "best"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"
    P360 = "360p"


class VideoContainer(StrEnum):
    """Supported output container preferences."""

    AUTO = "auto"
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"


class DownloadStatus(StrEnum):
    """Normalized stages emitted by a downloader."""

    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class VideoDownloadRequest:
    """Parameters required to download a single remote video."""

    source: MediaSource
    output_directory: Path
    quality: VideoQuality = VideoQuality.BEST
    container: VideoContainer = VideoContainer.AUTO


@dataclass(frozen=True, slots=True)
class DownloadProgress:
    """A point-in-time normalized download progress event."""

    status: DownloadStatus
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    speed_bytes_per_second: float | None = None
    eta_seconds: float | None = None
    filename: str | None = None

    @property
    def fraction(self) -> float | None:
        if self.downloaded_bytes is None or not self.total_bytes:
            return None
        return min(self.downloaded_bytes / self.total_bytes, 1.0)


@dataclass(frozen=True, slots=True)
class VideoDownloadResult:
    """Completed single-video download."""

    media_id: str
    title: str
    output_path: Path
    filesize_bytes: int
