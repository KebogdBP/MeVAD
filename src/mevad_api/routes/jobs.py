"""Background job lifecycle endpoints."""

from contextlib import suppress
from datetime import UTC, datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import FileResponse, JSONResponse

from mevad.exceptions import (
    InvalidJobTransitionError,
    InvalidSourceURLError,
    JobNotFoundError,
    JobQueueError,
    MediaProcessingError,
)
from mevad.jobs.models import Job, JobOperation, JobStatus
from mevad_api.abuse import AbuseProtectionError, AbuseProtector, client_key
from mevad_api.dependencies import (
    AbuseProtectorDependency,
    JobServiceDependency,
    SettingsDependency,
    WorkspaceManagerDependency,
)
from mevad_api.schemas import (
    CreateJobRequest,
    ErrorDetail,
    ErrorResponse,
    JobResponse,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_job(
    payload: CreateJobRequest,
    request: Request,
    settings: SettingsDependency,
    service: JobServiceDependency,
    abuse: AbuseProtectorDependency,
) -> JobResponse | JSONResponse:
    """Validate and enqueue one media job."""

    reservation: str | None = None
    job: Job | None = None
    try:
        identity = client_key(request, settings)
        rate = abuse.check_rate(
            identity,
            "create-job",
            limit=settings.job_create_rate_limit,
            window=settings.job_create_rate_window_seconds,
        )
        if not rate.allowed:
            return _error_response(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="rate_limit_exceeded",
                message="Too many job requests. Please retry later.",
                headers=_rate_headers(rate.limit, rate.remaining, rate.retry_after),
            )
        reservation = abuse.reserve_job(
            identity,
            limit=settings.anonymous_active_job_limit,
            ttl=settings.anonymous_job_slot_ttl_seconds,
        )
        if reservation is None:
            return _error_response(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="anonymous_job_limit_reached",
                message="Finish or cancel an active job before creating another.",
                headers={"Retry-After": "30"},
            )
        job = service.create(
            operation=JobOperation(payload.operation),
            source_url=payload.source_url,
            parameters=payload.options.model_dump(mode="json"),
        )
        abuse.bind_job(
            reservation,
            job.job_id,
            ttl=settings.anonymous_job_slot_ttl_seconds,
        )
    except AbuseProtectionError:
        if reservation is not None:
            _release_reservation_safely(abuse, reservation)
        if job is not None:
            # The durable job already exists; never hide its identifier from the caller.
            return _to_response(job)
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="abuse_protection_unavailable",
            message="Request protection is temporarily unavailable.",
        )
    except InvalidSourceURLError as error:
        if reservation is not None:
            _release_reservation_safely(abuse, reservation)
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_source_url",
            message=str(error),
        )
    except JobQueueError:
        if reservation is not None:
            _release_reservation_safely(abuse, reservation)
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="job_queue_unavailable",
            message="The media job could not be queued.",
        )
    return _to_response(job)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_job(
    job_id: str,
    service: JobServiceDependency,
    abuse: AbuseProtectorDependency,
) -> JobResponse | JSONResponse:
    """Return one job state."""

    try:
        job = service.get(job_id)
        if job.status.is_terminal:
            _release_job_safely(abuse, job_id)
        return _to_response(job)
    except JobNotFoundError:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_not_found",
            message="Job was not found.",
        )


@router.get(
    "/{job_id}/result",
    response_model=None,
    response_class=FileResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        410: {"model": ErrorResponse},
    },
)
def download_job_result(
    job_id: str,
    service: JobServiceDependency,
    workspaces: WorkspaceManagerDependency,
    abuse: AbuseProtectorDependency,
) -> FileResponse | JSONResponse:
    """Stream one completed, unexpired result from its confined workspace."""

    try:
        job = service.get(job_id)
    except JobNotFoundError:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_not_found",
            message="Job was not found.",
        )
    if job.status is not JobStatus.SUCCEEDED:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="job_result_not_ready",
            message="The job result is not ready.",
        )
    _release_job_safely(abuse, job_id)
    now = datetime.now(UTC)
    if (
        job.result_reference is None
        or job.storage_deleted_at is not None
        or job.result_expires_at is None
        or job.result_expires_at <= now
    ):
        return _result_unavailable()
    try:
        result_path = workspaces.resolve_result(job.job_id, job.result_reference)
    except MediaProcessingError:
        return _result_unavailable()
    return FileResponse(
        result_path,
        filename=result_path.name,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/{job_id}/cancel",
    response_model=JobResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def cancel_job(
    job_id: str,
    service: JobServiceDependency,
    abuse: AbuseProtectorDependency,
) -> JobResponse | JSONResponse:
    """Cancel a queued job or request cancellation from its worker."""

    try:
        job = service.cancel(job_id)
        if job.status.is_terminal:
            _release_job_safely(abuse, job_id)
        return _to_response(job)
    except JobNotFoundError:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_not_found",
            message="Job was not found.",
        )
    except InvalidJobTransitionError:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="job_not_cancellable",
            message="Job can no longer be cancelled.",
        )


def _to_response(job: Job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        operation=job.operation,
        source_url=job.source_url,
        parameters=dict(job.parameters),
        status=job.status,
        progress_percent=job.progress_percent,
        created_at=job.created_at,
        updated_at=job.updated_at,
        version=job.version,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        result_reference=job.result_reference,
        result_expires_at=job.result_expires_at,
        storage_deleted_at=job.storage_deleted_at,
        error_code=job.error_code,
        error_message=job.error_message,
    )


def _rate_headers(limit: int, remaining: int, retry_after: int) -> dict[str, str]:
    return {
        "Retry-After": str(retry_after),
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
    }


def _release_reservation_safely(abuse: AbuseProtector, reservation: str) -> None:
    with suppress(AbuseProtectionError):
        abuse.release_reservation(reservation)


def _release_job_safely(abuse: AbuseProtector, job_id: str) -> None:
    with suppress(AbuseProtectionError):
        abuse.release_job(job_id)


def _error_response(
    *, status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


def _result_unavailable() -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_410_GONE,
        code="job_result_unavailable",
        message="The job result has expired or is no longer available.",
    )
