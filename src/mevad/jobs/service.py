"""Job application service and lifecycle transitions."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import TypeAlias
from uuid import uuid4

from mevad.exceptions import InvalidJobTransitionError, JobNotFoundError
from mevad.jobs.models import Job, JobOperation, JobParameter, JobStatus
from mevad.jobs.repository import JobRepository
from mevad.security import normalize_remote_url

Clock: TypeAlias = Callable[[], datetime]
JobIdFactory: TypeAlias = Callable[[], str]


class JobService:
    """Create and transition jobs without running media work inline."""

    def __init__(
        self,
        repository: JobRepository,
        *,
        clock: Clock | None = None,
        job_id_factory: JobIdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or _utc_now
        self._job_id_factory = job_id_factory or _new_job_id

    def create(
        self,
        *,
        operation: JobOperation,
        source_url: str,
        parameters: Mapping[str, JobParameter],
    ) -> Job:
        now = self._clock()
        job = Job(
            job_id=self._job_id_factory(),
            operation=operation,
            source_url=normalize_remote_url(source_url),
            parameters=MappingProxyType(dict(parameters)),
            status=JobStatus.QUEUED,
            progress_percent=0,
            created_at=now,
            updated_at=now,
            version=1,
        )
        self._repository.add(job)
        return job

    def get(self, job_id: str) -> Job:
        job = self._repository.get(job_id)
        if job is None:
            raise JobNotFoundError("Job was not found.")
        return job

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job.status.is_terminal:
            raise InvalidJobTransitionError(f"Cannot cancel a job in {job.status.value} state.")
        target = (
            JobStatus.CANCELLED if job.status is JobStatus.QUEUED else JobStatus.CANCEL_REQUESTED
        )
        return self._transition(job, status=target)

    def start(self, job_id: str) -> Job:
        job = self.get(job_id)
        self._require_status(job, JobStatus.QUEUED)
        return self._transition(job, status=JobStatus.RUNNING)

    def mark_processing(self, job_id: str) -> Job:
        job = self.get(job_id)
        self._require_status(job, JobStatus.RUNNING)
        return self._transition(job, status=JobStatus.PROCESSING)

    def report_progress(self, job_id: str, progress_percent: int) -> Job:
        job = self.get(job_id)
        if job.status not in {JobStatus.RUNNING, JobStatus.PROCESSING}:
            raise InvalidJobTransitionError(
                f"Cannot report progress for a job in {job.status.value} state."
            )
        if not job.progress_percent <= progress_percent <= 99:
            raise InvalidJobTransitionError("Job progress must be monotonic and between 0 and 99.")
        return self._transition(job, progress_percent=progress_percent)

    def succeed(self, job_id: str, *, result_reference: str) -> Job:
        job = self.get(job_id)
        if job.status not in {JobStatus.RUNNING, JobStatus.PROCESSING}:
            raise InvalidJobTransitionError(f"Cannot complete a job in {job.status.value} state.")
        return self._transition(
            job,
            status=JobStatus.SUCCEEDED,
            progress_percent=100,
            result_reference=result_reference,
        )

    def fail(self, job_id: str, *, error_code: str, error_message: str) -> Job:
        job = self.get(job_id)
        if job.status not in {
            JobStatus.RUNNING,
            JobStatus.PROCESSING,
            JobStatus.CANCEL_REQUESTED,
        }:
            raise InvalidJobTransitionError(f"Cannot fail a job in {job.status.value} state.")
        return self._transition(
            job,
            status=JobStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
        )

    def acknowledge_cancellation(self, job_id: str) -> Job:
        job = self.get(job_id)
        self._require_status(job, JobStatus.CANCEL_REQUESTED)
        return self._transition(job, status=JobStatus.CANCELLED)

    def _transition(
        self,
        job: Job,
        *,
        status: JobStatus | None = None,
        progress_percent: int | None = None,
        result_reference: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> Job:
        updated = replace(
            job,
            status=status or job.status,
            progress_percent=(
                progress_percent if progress_percent is not None else job.progress_percent
            ),
            result_reference=(
                result_reference if result_reference is not None else job.result_reference
            ),
            error_code=error_code if error_code is not None else job.error_code,
            error_message=error_message if error_message is not None else job.error_message,
            updated_at=self._clock(),
            version=job.version + 1,
        )
        self._repository.update(updated, expected_version=job.version)
        return updated

    @staticmethod
    def _require_status(job: Job, expected: JobStatus) -> None:
        if job.status is not expected:
            raise InvalidJobTransitionError(
                f"Expected {expected.value} state, got {job.status.value}."
            )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_job_id() -> str:
    return str(uuid4())
