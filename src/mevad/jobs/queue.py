"""Job queue port and process-local reference adapter."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Condition
from typing import Protocol
from uuid import uuid4

from mevad.exceptions import JobQueueError


@dataclass(frozen=True, slots=True)
class JobClaim:
    """One exact broker delivery claimed by a worker."""

    job_id: str
    receipt: str
    claimed_at: datetime | None = None


ReceiptFactory = Callable[[], str]


class JobQueue(Protocol):
    """Broker boundary shared by the API and worker."""

    def enqueue(self, job_id: str) -> None:
        """Publish a job identifier."""
        ...

    def dequeue(self, *, timeout_seconds: int) -> JobClaim | None:
        """Claim one identifier, waiting up to the requested timeout."""
        ...

    def acknowledge(self, claim: JobClaim) -> None:
        """Remove a successfully handled identifier from in-flight storage."""
        ...

    def retry(self, claim: JobClaim, *, delay_seconds: int = 0) -> None:
        """Move a claim to ready now or after a non-blocking delay."""
        ...

    def dead_letter(self, claim: JobClaim) -> None:
        """Move an exhausted claimed identifier to dead-letter storage."""
        ...

    def recover_inflight(self) -> int:
        """Return abandoned claims to the ready queue."""
        ...

    def find_stale(self, *, before: datetime) -> tuple[JobClaim, ...]:
        """Return claims older than the supplied UTC deadline."""
        ...


class InMemoryJobQueue:
    """Thread-safe queue for tests and single-process development."""

    def __init__(
        self,
        *,
        receipt_factory: ReceiptFactory | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._items: deque[JobClaim] = deque()
        self._processing: dict[str, JobClaim] = {}
        self._dead_letters: deque[JobClaim] = deque()
        self._delayed: list[tuple[datetime, JobClaim]] = []
        self._condition = Condition()
        self._receipt_factory = receipt_factory or _new_receipt
        self._clock = clock or _utc_now

    def enqueue(self, job_id: str) -> None:
        with self._condition:
            receipt = self._receipt_factory()
            self._items.append(JobClaim(job_id=job_id, receipt=receipt))
            self._condition.notify()

    def dequeue(self, *, timeout_seconds: int) -> JobClaim | None:
        if timeout_seconds < 0:
            raise ValueError("Queue timeout cannot be negative.")
        with self._condition:
            self._promote_due()
            if not self._items:
                self._condition.wait(timeout_seconds)
                self._promote_due()
            if not self._items:
                return None
            queued = self._items.popleft()
            claim = JobClaim(
                job_id=queued.job_id,
                receipt=queued.receipt,
                claimed_at=self._clock(),
            )
            self._processing[claim.receipt] = claim
            return claim

    def acknowledge(self, claim: JobClaim) -> None:
        self._remove_processing(claim)

    def retry(self, claim: JobClaim, *, delay_seconds: int = 0) -> None:
        if delay_seconds < 0:
            raise ValueError("Retry delay cannot be negative.")
        self._remove_processing(claim)
        replacement = JobClaim(job_id=claim.job_id, receipt=self._receipt_factory())
        if delay_seconds == 0:
            self._items.append(replacement)
            return
        available_at = self._clock() + timedelta(seconds=delay_seconds)
        self._delayed.append((available_at, replacement))

    def dead_letter(self, claim: JobClaim) -> None:
        self._remove_processing(claim)
        self._dead_letters.append(claim)

    @property
    def dead_letters(self) -> tuple[str, ...]:
        return tuple(claim.job_id for claim in self._dead_letters)

    def recover_inflight(self) -> int:
        claims = tuple(self._processing.values())
        self._processing.clear()
        self._items.extend(claims)
        return len(claims)

    def find_stale(self, *, before: datetime) -> tuple[JobClaim, ...]:
        return tuple(
            claim
            for claim in self._processing.values()
            if claim.claimed_at is not None and claim.claimed_at <= before
        )

    def _remove_processing(self, claim: JobClaim) -> None:
        current = self._processing.get(claim.receipt)
        if current is None or current.job_id != claim.job_id:
            raise JobQueueError("Claimed job was not found in the processing queue.")
        del self._processing[claim.receipt]

    def _promote_due(self) -> None:
        now = self._clock()
        pending: list[tuple[datetime, JobClaim]] = []
        for available_at, claim in self._delayed:
            if available_at <= now:
                self._items.append(claim)
            else:
                pending.append((available_at, claim))
        self._delayed = pending


def _new_receipt() -> str:
    return uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(UTC)
