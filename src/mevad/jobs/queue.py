"""Job queue port and process-local reference adapter."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Condition
from typing import Protocol
from uuid import uuid4

from mevad.exceptions import JobQueueError


@dataclass(frozen=True, slots=True)
class JobClaim:
    """One exact broker delivery claimed by a worker."""

    job_id: str
    receipt: str


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

    def retry(self, claim: JobClaim) -> None:
        """Move a claimed identifier back to the ready queue."""
        ...

    def dead_letter(self, claim: JobClaim) -> None:
        """Move an exhausted claimed identifier to dead-letter storage."""
        ...

    def recover_inflight(self) -> int:
        """Return abandoned claims to the ready queue."""
        ...


class InMemoryJobQueue:
    """Thread-safe queue for tests and single-process development."""

    def __init__(self, *, receipt_factory: ReceiptFactory | None = None) -> None:
        self._items: deque[JobClaim] = deque()
        self._processing: dict[str, JobClaim] = {}
        self._dead_letters: deque[JobClaim] = deque()
        self._condition = Condition()
        self._receipt_factory = receipt_factory or _new_receipt

    def enqueue(self, job_id: str) -> None:
        with self._condition:
            receipt = self._receipt_factory()
            self._items.append(JobClaim(job_id=job_id, receipt=receipt))
            self._condition.notify()

    def dequeue(self, *, timeout_seconds: int) -> JobClaim | None:
        if timeout_seconds < 0:
            raise ValueError("Queue timeout cannot be negative.")
        with self._condition:
            if not self._items:
                self._condition.wait(timeout_seconds)
            if not self._items:
                return None
            claim = self._items.popleft()
            self._processing[claim.receipt] = claim
            return claim

    def acknowledge(self, claim: JobClaim) -> None:
        self._remove_processing(claim)

    def retry(self, claim: JobClaim) -> None:
        self._remove_processing(claim)
        self._items.append(JobClaim(job_id=claim.job_id, receipt=self._receipt_factory()))

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

    def _remove_processing(self, claim: JobClaim) -> None:
        current = self._processing.get(claim.receipt)
        if current != claim:
            raise JobQueueError("Claimed job was not found in the processing queue.")
        del self._processing[claim.receipt]


def _new_receipt() -> str:
    return uuid4().hex
