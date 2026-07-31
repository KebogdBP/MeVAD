"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Response, status

from mevad_api.dependencies import (
    MetricsRegistryDependency,
    RuntimeToolsDependency,
    SettingsDependency,
)
from mevad_api.schemas import LivenessResponse, ReadinessChecks, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/metrics", include_in_schema=False, response_model=None)
def metrics(
    settings: SettingsDependency,
    registry: MetricsRegistryDependency,
) -> Response:
    """Expose process metrics on the internal API listener only."""

    if not settings.metrics_enabled:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        content=registry.render(),
        media_type="text/plain; version=0.0.4",
        headers={"Cache-Control": "no-store"},
    )


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
