"""Long-running Redis/PostgreSQL worker process."""

import logging
import os
import signal
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import Event
from time import monotonic
from typing import Protocol
from uuid import uuid4

from mevad.exceptions import (
    ConcurrentJobUpdateError,
    InvalidJobTransitionError,
    JobNotFoundError,
)
from mevad.jobs import (
    Job,
    JobClaim,
    JobQueue,
    JobService,
    JobStatus,
    RetryBackoff,
    is_retryable_error,
)
from mevad.jobs.redis_queue import RedisJobQueue
from mevad.jobs.sql_repository import SqlJobRepository
from mevad_api.config import Settings
from mevad_worker.factory import create_default_executor

LOGGER = logging.getLogger("mevad.worker")


class JobRunner(Protocol):
    def execute(self, job_id: str, *, claim_receipt: str | None = None) -> Job:
        """Execute one claimed job."""
        ...


class WorkerRuntime:
    """Claim queued identifiers and execute them until shutdown."""

    def __init__(
        self,
        queue: JobQueue,
        service: JobService,
        executor: JobRunner,
        *,
        poll_timeout_seconds: int = 5,
        recovery_interval_seconds: int = 30,
        claim_stale_seconds: int = 120,
        retry_backoff: RetryBackoff | None = None,
    ) -> None:
        self._queue = queue
        self._service = service
        self._executor = executor
        self._poll_timeout_seconds = poll_timeout_seconds
        self._recovery_interval_seconds = recovery_interval_seconds
        self._claim_stale_seconds = claim_stale_seconds
        self._retry_backoff = retry_backoff or RetryBackoff()
        self._last_recovery = 0.0

    def recover(self) -> int:
        recovered = self._recover_unleased_claims()
        for candidate in self._service.find_expired():
            if candidate.claim_receipt is None:
                continue
            claim = JobClaim(
                job_id=candidate.job_id,
                receipt=candidate.claim_receipt,
            )
            try:
                expired = self._service.expire_lease(candidate.job_id)
            except (ConcurrentJobUpdateError, InvalidJobTransitionError):
                continue
            if expired.status is JobStatus.CANCELLED:
                self._queue.acknowledge(claim)
            elif self._can_retry(expired):
                self._service.retry(expired.job_id)
                self._queue.retry(
                    claim,
                    delay_seconds=self._retry_backoff.delay_seconds(
                        attempt_count=expired.attempt_count
                    ),
                )
            else:
                self._queue.dead_letter(claim)
            recovered += 1
        self._last_recovery = monotonic()
        return recovered

    def _recover_unleased_claims(self) -> int:
        before = datetime.now(UTC) - timedelta(seconds=self._claim_stale_seconds)
        recovered = 0
        for claim in self._queue.find_stale(before=before):
            try:
                job = self._service.get(claim.job_id)
            except JobNotFoundError:
                self._queue.acknowledge(claim)
                recovered += 1
                continue
            if job.status is JobStatus.QUEUED and job.claim_receipt is None:
                self._queue.retry(claim)
                recovered += 1
            elif job.status.is_terminal or (
                job.claim_receipt is not None and job.claim_receipt != claim.receipt
            ):
                self._queue.acknowledge(claim)
                recovered += 1
        return recovered

    def run_once(self) -> bool:
        if monotonic() - self._last_recovery >= self._recovery_interval_seconds:
            self.recover()
        claim = self._queue.dequeue(timeout_seconds=self._poll_timeout_seconds)
        if claim is None:
            return False
        try:
            result = self._executor.execute(
                claim.job_id,
                claim_receipt=claim.receipt,
            )
        except (InvalidJobTransitionError, JobNotFoundError):
            LOGGER.warning("Discarding stale queue entry for job %s", claim.job_id)
            self._queue.acknowledge(claim)
            return True
        if result.status is not JobStatus.FAILED:
            self._queue.acknowledge(claim)
            return True
        if self._can_retry(result):
            self._service.retry(claim.job_id)
            delay_seconds = self._retry_backoff.delay_seconds(attempt_count=result.attempt_count)
            self._queue.retry(claim, delay_seconds=delay_seconds)
            LOGGER.info(
                "Retrying job %s in %d seconds after attempt %d of %d",
                claim.job_id,
                delay_seconds,
                result.attempt_count,
                result.max_attempts,
            )
        else:
            self._queue.dead_letter(claim)
            LOGGER.warning(
                "Dead-lettered job %s after %d attempts",
                claim.job_id,
                result.attempt_count,
            )
        return True

    @staticmethod
    def _can_retry(job: Job) -> bool:
        return job.attempt_count < job.max_attempts and is_retryable_error(job.error_code)

    def run_forever(self, stop_requested: Callable[[], bool]) -> None:
        recovered = self.recover()
        if recovered:
            LOGGER.info("Recovered %d in-flight jobs", recovered)
        while not stop_requested():
            self.run_once()


def create_runtime(settings: Settings | None = None) -> WorkerRuntime:
    """Compose a production worker from environment-backed settings."""

    selected = settings or Settings()
    if selected.job_backend != "postgres" or selected.queue_backend != "redis":
        raise RuntimeError("Worker requires postgres job backend and redis queue backend.")
    repository = SqlJobRepository.from_url(selected.database_url)
    if selected.auto_create_schema:
        repository.create_schema()
    queue = RedisJobQueue.from_url(
        selected.redis_url,
        queue_name=selected.redis_queue_name,
    )
    service = JobService(
        repository,
        storage_retention_seconds=selected.storage_retention_seconds,
    )
    worker_id = selected.worker_id or f"worker-{os.getpid()}-{uuid4().hex[:12]}"
    return WorkerRuntime(
        queue,
        service,
        create_default_executor(
            service,
            storage_root=selected.storage_root,
            media_timeout_seconds=selected.worker_media_timeout_seconds,
            worker_id=worker_id,
            lease_duration_seconds=selected.worker_lease_seconds,
            heartbeat_interval_seconds=selected.worker_heartbeat_seconds,
        ),
        poll_timeout_seconds=selected.worker_poll_timeout_seconds,
        recovery_interval_seconds=selected.worker_recovery_interval_seconds,
        claim_stale_seconds=selected.worker_claim_stale_seconds,
        retry_backoff=RetryBackoff(
            base_seconds=selected.worker_retry_base_seconds,
            max_seconds=selected.worker_retry_max_seconds,
        ),
    )


def main() -> None:
    """Run the worker until SIGINT or SIGTERM."""

    logging.basicConfig(level=logging.INFO)
    stop_event = Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    create_runtime().run_forever(stop_event.is_set)
