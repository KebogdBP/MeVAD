"""Job application service and lifecycle transitions."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import TypeAlias
from uuid import uuid4

from mevad.exceptions import InvalidJobTransitionError, JobNotFoundError, JobQueueError
from mevad.jobs.models import Job, JobOperation, JobParameter, JobStatus
from mevad.jobs.outbox import JobOutbox
from mevad.jobs.queue import JobQueue
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
        queue: JobQueue | None = None,
        outbox: JobOutbox | None = None,
        default_max_attempts: int = 3,
        storage_retention_seconds: int = 86400,
        clock: Clock | None = None,
        job_id_factory: JobIdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._queue = queue
        if queue is not None and outbox is not None:
            raise ValueError("Job service cannot use direct queue and outbox together.")
        self._outbox = outbox
        if not 1 <= default_max_attempts <= 10:
            raise ValueError("Default max attempts must be between 1 and 10.")
        self._default_max_attempts = default_max_attempts
        if not 60 <= storage_retention_seconds <= 2592000:
            raise ValueError("Storage retention must be between 60 and 2592000 seconds.")
        self._storage_retention_seconds = storage_retention_seconds
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
            max_attempts=self._default_max_attempts,
        )
        if self._outbox is not None:
            self._outbox.add(job)
        else:
            self._repository.add(job)
        if self._queue is not None:
            try:
                self._queue.enqueue(job.job_id)
            except Exception as error:
                self._transition(
                    job,
                    status=JobStatus.FAILED,
                    error_code="job_enqueue_failed",
                    error_message="The media job could not be queued.",
                )
                raise JobQueueError("The media job could not be queued.") from error
        return job

    def get(self, job_id: str) -> Job:
        job = self._repository.get(job_id)
        if job is None:
            raise JobNotFoundError("Job was not found.")
        return job

    def close(self) -> None:
        """Release repository resources owned by this service."""

        self._repository.close()

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job.status.is_terminal:
            raise InvalidJobTransitionError(f"Cannot cancel a job in {job.status.value} state.")
        target = (
            JobStatus.CANCELLED if job.status is JobStatus.QUEUED else JobStatus.CANCEL_REQUESTED
        )
        return self._transition(job, status=target)

    def start(
        self,
        job_id: str,
        *,
        worker_id: str | None = None,
        claim_receipt: str | None = None,
        lease_duration_seconds: int = 60,
    ) -> Job:
        job = self.get(job_id)
        self._require_status(job, JobStatus.QUEUED)
        lease_expires_at = None
        if worker_id is not None:
            _validate_worker_id(worker_id)
            _validate_lease_duration(lease_duration_seconds)
            lease_expires_at = self._clock() + timedelta(seconds=lease_duration_seconds)
        if claim_receipt is not None and not 1 <= len(claim_receipt) <= 4096:
            raise ValueError("Claim receipt must be between 1 and 4096 characters.")
        return self._transition(
            job,
            status=JobStatus.RUNNING,
            attempt_count=job.attempt_count + 1,
            lease_owner=worker_id,
            lease_expires_at=lease_expires_at,
            claim_receipt=claim_receipt,
        )

    def heartbeat(
        self,
        job_id: str,
        *,
        worker_id: str,
        lease_duration_seconds: int,
    ) -> Job:
        """Extend a live job lease owned by this worker."""

        _validate_lease_duration(lease_duration_seconds)
        job = self.get(job_id)
        if job.status not in {
            JobStatus.RUNNING,
            JobStatus.PROCESSING,
            JobStatus.CANCEL_REQUESTED,
        }:
            raise InvalidJobTransitionError("Job is not leased in its current state.")
        if job.lease_owner != worker_id:
            raise InvalidJobTransitionError("Job lease is owned by another worker.")
        now = self._clock()
        if job.lease_expires_at is None or job.lease_expires_at <= now:
            raise InvalidJobTransitionError("Job lease has expired.")
        updated = replace(
            job,
            lease_expires_at=now + timedelta(seconds=lease_duration_seconds),
            updated_at=now,
            version=job.version + 1,
        )
        self._repository.update(updated, expected_version=job.version)
        return updated

    def find_expired(self, *, limit: int = 100) -> tuple[Job, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("Expired job limit must be between 1 and 1000.")
        return self._repository.find_expired(now=self._clock(), limit=limit)

    def expire_lease(self, job_id: str) -> Job:
        """Fail or cancel a job whose persisted lease is no longer live."""

        job = self.get(job_id)
        now = self._clock()
        if job.lease_expires_at is None or job.lease_expires_at > now:
            raise InvalidJobTransitionError("Job lease has not expired.")
        if job.status is JobStatus.CANCEL_REQUESTED:
            return self._transition(job, status=JobStatus.CANCELLED, clear_lease=True)
        if job.status not in {JobStatus.RUNNING, JobStatus.PROCESSING}:
            raise InvalidJobTransitionError("Job cannot expire in its current state.")
        return self._transition(
            job,
            status=JobStatus.FAILED,
            error_code="worker_lease_expired",
            error_message="The worker stopped reporting job health.",
            clear_lease=True,
        )

    def retry(self, job_id: str) -> Job:
        """Reset a failed job for another bounded execution attempt."""

        job = self.get(job_id)
        self._require_status(job, JobStatus.FAILED)
        if job.attempt_count >= job.max_attempts:
            raise InvalidJobTransitionError("Job retry attempts are exhausted.")
        updated = replace(
            job,
            status=JobStatus.QUEUED,
            progress_percent=0,
            result_reference=None,
            result_expires_at=None,
            storage_deleted_at=None,
            error_code=None,
            error_message=None,
            lease_owner=None,
            lease_expires_at=None,
            claim_receipt=None,
            updated_at=self._clock(),
            version=job.version + 1,
        )
        self._repository.update(updated, expected_version=job.version)
        return updated

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
            clear_lease=True,
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
            clear_lease=True,
        )

    def acknowledge_cancellation(self, job_id: str) -> Job:
        job = self.get(job_id)
        self._require_status(job, JobStatus.CANCEL_REQUESTED)
        return self._transition(job, status=JobStatus.CANCELLED, clear_lease=True)

    def _transition(
        self,
        job: Job,
        *,
        status: JobStatus | None = None,
        progress_percent: int | None = None,
        attempt_count: int | None = None,
        lease_owner: str | None = None,
        lease_expires_at: datetime | None = None,
        claim_receipt: str | None = None,
        clear_lease: bool = False,
        result_reference: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> Job:
        now = self._clock()
        target_status = status or job.status
        updated = replace(
            job,
            status=target_status,
            progress_percent=(
                progress_percent if progress_percent is not None else job.progress_percent
            ),
            attempt_count=(attempt_count if attempt_count is not None else job.attempt_count),
            lease_owner=None if clear_lease else (lease_owner or job.lease_owner),
            lease_expires_at=(
                None
                if clear_lease
                else (lease_expires_at if lease_expires_at is not None else job.lease_expires_at)
            ),
            claim_receipt=(None if clear_lease else (claim_receipt or job.claim_receipt)),
            result_reference=(
                result_reference if result_reference is not None else job.result_reference
            ),
            error_code=error_code if error_code is not None else job.error_code,
            error_message=error_message if error_message is not None else job.error_message,
            result_expires_at=(
                now + timedelta(seconds=self._storage_retention_seconds)
                if target_status.is_terminal and not job.status.is_terminal
                else job.result_expires_at
            ),
            updated_at=now,
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


def _validate_worker_id(worker_id: str) -> None:
    if not worker_id or len(worker_id) > 128 or not worker_id.isascii():
        raise ValueError("Worker identifier must be 1-128 ASCII characters.")


def _validate_lease_duration(seconds: int) -> None:
    if not 5 <= seconds <= 3600:
        raise ValueError("Lease duration must be between 5 and 3600 seconds.")
