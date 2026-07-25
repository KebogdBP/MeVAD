"""Job queue port and process-local reference adapter."""

from collections import deque
from threading import Condition
from typing import Protocol


class JobQueue(Protocol):
    """Broker boundary shared by the API and worker."""

    def enqueue(self, job_id: str) -> None:
        """Publish a job identifier."""
        ...

    def dequeue(self, *, timeout_seconds: int) -> str | None:
        """Claim one identifier, waiting up to the requested timeout."""
        ...

    def acknowledge(self, job_id: str) -> None:
        """Remove a successfully handled identifier from in-flight storage."""
        ...

    def recover_inflight(self) -> int:
        """Return abandoned claims to the ready queue."""
        ...


class InMemoryJobQueue:
    """Thread-safe queue for tests and single-process development."""

    def __init__(self) -> None:
        self._items: deque[str] = deque()
        self._condition = Condition()

    def enqueue(self, job_id: str) -> None:
        with self._condition:
            self._items.append(job_id)
            self._condition.notify()

    def dequeue(self, *, timeout_seconds: int) -> str | None:
        if timeout_seconds < 0:
            raise ValueError("Queue timeout cannot be negative.")
        with self._condition:
            if not self._items:
                self._condition.wait(timeout_seconds)
            return self._items.popleft() if self._items else None

    def acknowledge(self, job_id: str) -> None:
        """In-memory dequeue is already destructive."""

    def recover_inflight(self) -> int:
        return 0
