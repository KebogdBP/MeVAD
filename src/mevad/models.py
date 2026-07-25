"""Typed domain models shared by CLI and future application adapters."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path

from mevad.exceptions import InvalidClipIntervalError


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


class AudioCodec(StrEnum):
    """Supported extracted-audio output codecs."""

    MP3 = "mp3"
    M4A = "m4a"
    OPUS = "opus"
    WAV = "wav"


class AudioBitrate(StrEnum):
    """User-facing compressed-audio bitrate presets."""

    K128 = "128"
    K192 = "192"
    K256 = "256"
    K320 = "320"


@dataclass(frozen=True, slots=True)
class AudioExtractionRequest:
    """Parameters required to extract audio from one remote media source."""

    source: MediaSource
    output_directory: Path
    codec: AudioCodec = AudioCodec.MP3
    bitrate: AudioBitrate = AudioBitrate.K192


@dataclass(frozen=True, slots=True)
class AudioExtractionResult:
    """Completed audio extraction result."""

    media_id: str
    title: str
    codec: AudioCodec
    output_path: Path
    filesize_bytes: int


class CutMode(StrEnum):
    """Video cutting accuracy and performance modes."""

    FAST = "fast"
    ACCURATE = "accurate"


@dataclass(frozen=True, slots=True)
class ClipInterval:
    """Validated half-open media interval in seconds."""

    start_seconds: float
    end_seconds: float

    def __post_init__(self) -> None:
        if not isfinite(self.start_seconds) or not isfinite(self.end_seconds):
            raise InvalidClipIntervalError("Clip timestamps must be finite.")
        if self.start_seconds < 0:
            raise InvalidClipIntervalError("Clip start must not be negative.")
        if self.end_seconds <= self.start_seconds:
            raise InvalidClipIntervalError("Clip end must be greater than clip start.")

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True, slots=True)
class VideoCutRequest:
    """Parameters required to cut a local video file."""

    input_path: Path
    output_directory: Path
    interval: ClipInterval
    mode: CutMode = CutMode.ACCURATE


@dataclass(frozen=True, slots=True)
class VideoCutResult:
    """Completed local video cut."""

    output_path: Path
    duration_seconds: float
    filesize_bytes: int
    mode: CutMode
