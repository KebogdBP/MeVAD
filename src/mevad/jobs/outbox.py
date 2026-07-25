"""Transactional job outbox contracts and relay."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from mevad.exceptions import JobQueueError
from mevad.jobs.models import Job
from mevad.jobs.queue import JobQueue


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    """One durable request to publish a job identifier."""

    event_id: str
    job_id: str
    created_at: datetime
    attempt_count: int = 0
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None


class JobOutbox(Protocol):
    """Atomically persist a job and its publication intent."""

    def add(self, job: Job) -> None: ...


class OutboxStore(Protocol):
    """Durable relay-facing outbox operations."""

    def claim_outbox(
        self,
        *,
        owner: str,
        now: datetime,
        lease_seconds: int,
        limit: int,
    ) -> tuple[OutboxEvent, ...]: ...

    def mark_outbox_published(
        self,
        event_id: str,
        *,
        owner: str,
        published_at: datetime,
    ) -> None: ...

    def release_outbox(self, event_id: str, *, owner: str, error_message: str) -> None: ...

    def close(self) -> None: ...


class SqlJobOutbox:
    """SQL repository adapter used by JobService."""

    def __init__(
        self,
        repository: "AtomicOutboxRepository",
        *,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._event_id_factory = event_id_factory or _new_event_id

    def add(self, job: Job) -> None:
        self._repository.add_with_outbox(
            job,
            OutboxEvent(
                event_id=self._event_id_factory(),
                job_id=job.job_id,
                created_at=job.created_at,
            ),
        )


class AtomicOutboxRepository(Protocol):
    def add_with_outbox(self, job: Job, event: OutboxEvent) -> None: ...


class OutboxRelay:
    """Publish leased outbox events with at-least-once delivery."""

    def __init__(
        self,
        store: OutboxStore,
        queue: JobQueue,
        *,
        owner: str,
        clock: Callable[[], datetime],
        lease_seconds: int = 30,
        batch_size: int = 100,
    ) -> None:
        self._store = store
        self._queue = queue
        self._owner = owner
        self._clock = clock
        self._lease_seconds = lease_seconds
        self._batch_size = batch_size

    def run_once(self) -> int:
        events = self._store.claim_outbox(
            owner=self._owner,
            now=self._clock(),
            lease_seconds=self._lease_seconds,
            limit=self._batch_size,
        )
        published = 0
        for event in events:
            try:
                self._queue.enqueue(event.job_id)
            except JobQueueError:
                self._store.release_outbox(
                    event.event_id,
                    owner=self._owner,
                    error_message="Queue publication failed.",
                )
                continue
            self._store.mark_outbox_published(
                event.event_id,
                owner=self._owner,
                published_at=self._clock(),
            )
            published += 1
        return published

    def close(self) -> None:
        """Release durable store resources."""

        self._store.close()


def _new_event_id() -> str:
    return str(uuid4())
