"""Media analysis HTTP routes."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from mevad.exceptions import InvalidSourceURLError, MediaAnalysisError
from mevad.models import MediaAnalysis, MediaSource, SourceKind
from mevad_api.dependencies import AnalyzerDependency, SettingsDependency
from mevad_api.schemas import (
    AnalyzeMediaRequest,
    ErrorDetail,
    ErrorResponse,
    MediaAnalysisResponse,
    MediaFormatResponse,
)

router = APIRouter(prefix="/media", tags=["media"])


@router.post(
    "/analyze",
    response_model=MediaAnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def analyze_media(
    payload: AnalyzeMediaRequest,
    settings: SettingsDependency,
    analyzer: AnalyzerDependency,
) -> MediaAnalysisResponse | JSONResponse:
    """Analyze one remote media URL when the safe network feature is enabled."""

    if not settings.analyzer_enabled:
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="analyzer_disabled",
            message="Remote media analysis is disabled.",
        )

    source = MediaSource(kind=SourceKind.REMOTE_URL, value=payload.url)
    try:
        analysis = await run_in_threadpool(analyzer.analyze, source)
    except InvalidSourceURLError as error:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_source_url",
            message=str(error),
        )
    except MediaAnalysisError:
        return _error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="media_analysis_failed",
            message="The media source could not be analyzed.",
        )
    return _to_response(analysis)


def _to_response(analysis: MediaAnalysis) -> MediaAnalysisResponse:
    return MediaAnalysisResponse(
        source_url=analysis.source.value,
        extractor=analysis.extractor,
        media_id=analysis.media_id,
        title=analysis.title,
        author=analysis.author,
        duration_seconds=analysis.duration_seconds,
        thumbnail_url=analysis.thumbnail_url,
        webpage_url=analysis.webpage_url,
        is_playlist=analysis.is_playlist,
        playlist_entry_count=analysis.playlist_entry_count,
        formats=[
            MediaFormatResponse(
                format_id=media_format.format_id,
                extension=media_format.extension,
                width=media_format.width,
                height=media_format.height,
                fps=media_format.fps,
                filesize_bytes=media_format.filesize_bytes,
                has_video=media_format.has_video,
                has_audio=media_format.has_audio,
            )
            for media_format in analysis.formats
        ],
        subtitle_languages=list(analysis.subtitle_languages),
        available_actions=list(analysis.available_actions),
    )


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )
