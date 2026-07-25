"""Job repository port and in-memory reference adapter."""

from datetime import datetime
from threading import RLock
from typing import Protocol

from mevad.exceptions import ConcurrentJobUpdateError
from mevad.jobs.models import Job


class JobRepository(Protocol):
    """Persistence boundary for immutable jobs."""

    def add(self, job: Job) -> None:
        """Insert a new job."""
        ...

    def get(self, job_id: str) -> Job | None:
        """Return a job by identifier."""
        ...

    def update(self, job: Job, *, expected_version: int) -> None:
        """Replace a job if its current version matches."""
        ...

    def find_expired(self, *, now: datetime, limit: int) -> tuple[Job, ...]:
        """Return non-terminal jobs with expired worker leases."""
        ...


class InMemoryJobRepository:
    """Thread-safe process-local repository for tests and development."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = RLock()

    def add(self, job: Job) -> None:
        with self._lock:
            if job.job_id in self._jobs:
                raise ConcurrentJobUpdateError("Job identifier already exists.")
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: Job, *, expected_version: int) -> None:
        with self._lock:
            current = self._jobs.get(job.job_id)
            if current is None or current.version != expected_version:
                raise ConcurrentJobUpdateError("Job was updated concurrently.")
            self._jobs[job.job_id] = job

    def find_expired(self, *, now: datetime, limit: int) -> tuple[Job, ...]:
        with self._lock:
            expired = (
                job
                for job in self._jobs.values()
                if not job.status.is_terminal
                and job.lease_expires_at is not None
                and job.lease_expires_at <= now
            )
            return tuple(sorted(expired, key=lambda job: job.lease_expires_at or now)[:limit])
