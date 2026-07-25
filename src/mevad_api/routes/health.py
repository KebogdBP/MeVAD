"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Response, status

from mevad_api.dependencies import RuntimeToolsDependency, SettingsDependency
from mevad_api.schemas import LivenessResponse, ReadinessChecks, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
def liveness(settings: SettingsDependency) -> LivenessResponse:
    """Confirm that the API process can serve requests."""

    return LivenessResponse(
        service="mevad-api",
        version=settings.app_version,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
def readiness(
    response: Response,
    settings: SettingsDependency,
    tools: RuntimeToolsDependency,
) -> ReadinessResponse:
    """Confirm required local media tools are available."""

    checks = ReadinessChecks(
        core=True,
        ffmpeg=tools.ffmpeg is not None,
        ffprobe=tools.ffprobe is not None,
    )
    ready = not settings.require_media_tools or (checks.ffmpeg and checks.ffprobe)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        checks=checks,
    )
