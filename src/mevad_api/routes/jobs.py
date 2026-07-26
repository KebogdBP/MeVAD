"""Background job lifecycle endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, status
from fastapi.responses import FileResponse, JSONResponse

from mevad.exceptions import (
    InvalidJobTransitionError,
    InvalidSourceURLError,
    JobNotFoundError,
    JobQueueError,
    MediaProcessingError,
)
from mevad.jobs.models import Job, JobOperation, JobStatus
from mevad_api.dependencies import JobServiceDependency, WorkspaceManagerDependency
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
        503: {"model": ErrorResponse},
    },
)
def create_job(
    payload: CreateJobRequest,
    service: JobServiceDependency,
) -> JobResponse | JSONResponse:
    """Validate and enqueue one media job."""

    try:
        job = service.create(
            operation=JobOperation(payload.operation),
            source_url=payload.source_url,
            parameters=payload.options.model_dump(mode="json"),
        )
    except InvalidSourceURLError as error:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_source_url",
            message=str(error),
        )
    except JobQueueError:
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
) -> JobResponse | JSONResponse:
    """Return one job state."""

    try:
        return _to_response(service.get(job_id))
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
) -> JobResponse | JSONResponse:
    """Cancel a queued job or request cancellation from its worker."""

    try:
        return _to_response(service.cancel(job_id))
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


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def _result_unavailable() -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_410_GONE,
        code="job_result_unavailable",
        message="The job result has expired or is no longer available.",
    )
