"""Job repository port and in-memory reference adapter."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from threading import RLock
from typing import Protocol

from mevad.exceptions import ConcurrentJobUpdateError
from mevad.jobs.models import Job


@dataclass(frozen=True, slots=True)
class StorageCleanupClaim:
    job_id: str
    result_expires_at: datetime


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

    def close(self) -> None:
        """Release resources owned by the repository."""
        ...

    def claim_storage_cleanup(
        self,
        *,
        owner: str,
        now: datetime,
        lease_seconds: int,
        limit: int,
    ) -> tuple[StorageCleanupClaim, ...]: ...

    def complete_storage_cleanup(
        self,
        job_id: str,
        *,
        owner: str,
        completed_at: datetime,
    ) -> None: ...

    def release_storage_cleanup(self, job_id: str, *, owner: str) -> None: ...


class InMemoryJobRepository:
    """Thread-safe process-local repository for tests and development."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._cleanup_leases: dict[str, tuple[str, datetime]] = {}
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
            if (
                current is None
                or current.version != expected_version
                or job.job_id in self._cleanup_leases
            ):
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

    def close(self) -> None:
        """No-op for the process-local adapter."""

    def claim_storage_cleanup(
        self,
        *,
        owner: str,
        now: datetime,
        lease_seconds: int,
        limit: int,
    ) -> tuple[StorageCleanupClaim, ...]:
        with self._lock:
            claims: list[StorageCleanupClaim] = []
            for job in sorted(self._jobs.values(), key=lambda item: item.updated_at):
                lease = self._cleanup_leases.get(job.job_id)
                if (
                    len(claims) >= limit
                    or not job.status.is_terminal
                    or job.result_expires_at is None
                    or job.result_expires_at > now
                    or job.storage_deleted_at is not None
                    or (lease is not None and lease[1] > now)
                ):
                    continue
                self._cleanup_leases[job.job_id] = (
                    owner,
                    now + timedelta(seconds=lease_seconds),
                )
                self._jobs[job.job_id] = replace(
                    job,
                    updated_at=now,
                    version=job.version + 1,
                )
                claims.append(
                    StorageCleanupClaim(
                        job_id=job.job_id,
                        result_expires_at=job.result_expires_at,
                    )
                )
            return tuple(claims)

    def complete_storage_cleanup(
        self,
        job_id: str,
        *,
        owner: str,
        completed_at: datetime,
    ) -> None:
        with self._lock:
            lease = self._cleanup_leases.get(job_id)
            job = self._jobs.get(job_id)
            if lease is None or lease[0] != owner or job is None:
                raise ConcurrentJobUpdateError("Storage cleanup lease is no longer owned.")
            self._jobs[job_id] = replace(
                job,
                result_reference=None,
                storage_deleted_at=completed_at,
                updated_at=completed_at,
                version=job.version + 1,
            )
            del self._cleanup_leases[job_id]

    def release_storage_cleanup(self, job_id: str, *, owner: str) -> None:
        with self._lock:
            lease = self._cleanup_leases.get(job_id)
            if lease is None or lease[0] != owner:
                raise ConcurrentJobUpdateError("Storage cleanup lease is no longer owned.")
            del self._cleanup_leases[job_id]
