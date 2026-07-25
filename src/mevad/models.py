"""Typed domain models shared by CLI and future application adapters."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path

from mevad.exceptions import InvalidClipIntervalError, MediaProcessingError


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


class LoopFormat(StrEnum):
    """Supported animated and loop-ready output formats."""

    GIF = "gif"
    WEBP = "webp"
    MP4 = "mp4"
    WEBM = "webm"


class LoopQuality(StrEnum):
    """Output quality presets mapped to trusted encoder settings."""

    SMALL = "small"
    BALANCED = "balanced"
    HIGH = "high"


class PlaybackSpeed(StrEnum):
    """Supported playback speed multipliers."""

    HALF = "0.5"
    NORMAL = "1"
    X1_5 = "1.5"
    DOUBLE = "2"

    @property
    def multiplier(self) -> float:
        return float(self.value)


@dataclass(frozen=True, slots=True)
class LoopRenderRequest:
    """Parameters required to render an animation or loop-ready video."""

    input_path: Path
    output_directory: Path
    interval: ClipInterval
    output_format: LoopFormat = LoopFormat.GIF
    width: int = 640
    fps: int = 15
    quality: LoopQuality = LoopQuality.BALANCED
    speed: PlaybackSpeed = PlaybackSpeed.NORMAL
    repeat: bool = True

    def __post_init__(self) -> None:
        if not 160 <= self.width <= 1920:
            raise MediaProcessingError("Loop width must be between 160 and 1920 pixels.")
        if not 1 <= self.fps <= 60:
            raise MediaProcessingError("Loop FPS must be between 1 and 60.")
        if self.output_format in {LoopFormat.GIF, LoopFormat.WEBP}:
            if self.interval.duration_seconds > 30:
                raise MediaProcessingError(
                    "GIF and WebP source duration must not exceed 30 seconds."
                )
            if self.fps > 30:
                raise MediaProcessingError("GIF and WebP FPS must not exceed 30.")
            if self.width > 1280:
                raise MediaProcessingError("GIF and WebP width must not exceed 1280 pixels.")
        elif self.interval.duration_seconds > 120:
            raise MediaProcessingError("Video loop source duration must not exceed 120 seconds.")

    @property
    def output_duration_seconds(self) -> float:
        return self.interval.duration_seconds / self.speed.multiplier


@dataclass(frozen=True, slots=True)
class LoopRenderResult:
    """Completed animation or loop-ready video."""

    output_path: Path
    output_format: LoopFormat
    duration_seconds: float
    width: int
    fps: int
    filesize_bytes: int
