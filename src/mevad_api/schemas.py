"""Versioned API request and response schemas."""

from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator

from mevad.jobs.models import JobOperation, JobParameter, JobStatus
from mevad.models import MediaAction


class ErrorDetail(BaseModel):
    """Machine-readable API error."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Stable error envelope."""

    error: ErrorDetail


class LivenessResponse(BaseModel):
    """Liveness probe response."""

    status: Literal["ok"] = "ok"
    service: str
    version: str


class ReadinessChecks(BaseModel):
    """Individual readiness dependencies."""

    core: bool
    ffmpeg: bool
    ffprobe: bool


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    status: Literal["ready", "not_ready"]
    checks: ReadinessChecks


class AnalyzeMediaRequest(BaseModel):
    """Remote media analysis input."""

    url: str = Field(min_length=1, max_length=2048)


class MediaFormatResponse(BaseModel):
    """Normalized downloadable media format."""

    format_id: str
    extension: str | None
    width: int | None
    height: int | None
    fps: float | None
    filesize_bytes: int | None
    has_video: bool
    has_audio: bool


class MediaAnalysisResponse(BaseModel):
    """Public normalized analyzer result."""

    source_url: str
    extractor: str
    media_id: str
    title: str
    author: str | None
    duration_seconds: float | None
    thumbnail_url: str | None
    webpage_url: str
    is_playlist: bool
    playlist_entry_count: int | None
    formats: list[MediaFormatResponse]
    subtitle_languages: list[str]
    available_actions: list[MediaAction]


class VideoDownloadJobOptions(BaseModel):
    """Video download job options."""

    quality: Literal["best", "1080p", "720p", "480p", "360p"] = "best"
    container: Literal["auto", "mp4", "mkv", "webm"] = "auto"


class AudioExtractionJobOptions(BaseModel):
    """Audio extraction job options."""

    codec: Literal["mp3", "m4a", "opus", "wav"] = "mp3"
    bitrate: Literal["128", "192", "256", "320"] = "192"


class ClipJobOptions(BaseModel):
    """Remote source clip job options."""

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    mode: Literal["fast", "accurate"] = "accurate"

    @model_validator(mode="after")
    def validate_interval(self) -> "ClipJobOptions":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class LoopJobOptions(BaseModel):
    """Remote source GIF/loop job options."""

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    output_format: Literal["gif", "webp", "mp4", "webm"] = "gif"
    width: int = Field(default=640, ge=160, le=1920)
    fps: int = Field(default=15, ge=1, le=60)
    quality: Literal["small", "balanced", "high"] = "balanced"
    speed: Literal["0.5", "1", "1.5", "2"] = "1"
    repeat: bool = True

    @model_validator(mode="after")
    def validate_render_limits(self) -> "LoopJobOptions":
        duration = self.end_seconds - self.start_seconds
        if duration <= 0:
            raise ValueError("end_seconds must be greater than start_seconds")
        if self.output_format in {"gif", "webp"}:
            if duration > 30:
                raise ValueError("GIF and WebP duration must not exceed 30 seconds")
            if self.width > 1280:
                raise ValueError("GIF and WebP width must not exceed 1280 pixels")
            if self.fps > 30:
                raise ValueError("GIF and WebP FPS must not exceed 30")
        elif duration > 120:
            raise ValueError("Video loop duration must not exceed 120 seconds")
        return self


class CreateVideoDownloadJobRequest(BaseModel):
    """Create a video download job."""

    operation: Literal["download_video"]
    source_url: str = Field(min_length=1, max_length=2048)
    options: VideoDownloadJobOptions = Field(default_factory=VideoDownloadJobOptions)


class CreateAudioExtractionJobRequest(BaseModel):
    """Create an audio extraction job."""

    operation: Literal["extract_audio"]
    source_url: str = Field(min_length=1, max_length=2048)
    options: AudioExtractionJobOptions = Field(default_factory=AudioExtractionJobOptions)


class CreateClipJobRequest(BaseModel):
    """Create a remote video clip job."""

    operation: Literal["cut_video"]
    source_url: str = Field(min_length=1, max_length=2048)
    options: ClipJobOptions


class CreateLoopJobRequest(BaseModel):
    """Create a remote GIF/loop job."""

    operation: Literal["make_loop"]
    source_url: str = Field(min_length=1, max_length=2048)
    options: LoopJobOptions


CreateJobRequest: TypeAlias = Annotated[
    CreateVideoDownloadJobRequest
    | CreateAudioExtractionJobRequest
    | CreateClipJobRequest
    | CreateLoopJobRequest,
    Field(discriminator="operation"),
]


class JobResponse(BaseModel):
    """Public background job state."""

    job_id: str
    operation: JobOperation
    source_url: str
    parameters: dict[str, JobParameter]
    status: JobStatus
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    version: int
    attempt_count: int
    max_attempts: int
    result_reference: str | None
    error_code: str | None
    error_message: str | None
