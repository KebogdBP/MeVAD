"""Versioned API request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

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
