"""Leased TTL cleanup for terminal job workspaces."""

import logging
import os
import signal
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Event
from uuid import uuid4

from mevad.exceptions import ConcurrentJobUpdateError, MediaProcessingError
from mevad.jobs.repository import JobRepository
from mevad.jobs.sql_repository import SqlJobRepository
from mevad_api.config import Settings
from mevad_worker.storage import WorkspaceManager

LOGGER = logging.getLogger("mevad.cleanup")


class StorageCleaner:
    """Delete expired terminal workspaces claimed from durable state."""

    def __init__(
        self,
        repository: JobRepository,
        workspaces: WorkspaceManager,
        *,
        owner: str,
        clock: Callable[[], datetime],
        lease_seconds: int = 300,
        batch_size: int = 100,
    ) -> None:
        self._repository = repository
        self._workspaces = workspaces
        self._owner = owner
        self._clock = clock
        self._lease_seconds = lease_seconds
        self._batch_size = batch_size

    def run_once(self) -> int:
        claims = self._repository.claim_storage_cleanup(
            owner=self._owner,
            now=self._clock(),
            lease_seconds=self._lease_seconds,
            limit=self._batch_size,
        )
        completed = 0
        for claim in claims:
            try:
                self._workspaces.cleanup_job(claim.job_id)
            except (MediaProcessingError, OSError):
                self._repository.release_storage_cleanup(
                    claim.job_id,
                    owner=self._owner,
                )
                continue
            try:
                self._repository.complete_storage_cleanup(
                    claim.job_id,
                    owner=self._owner,
                    completed_at=self._clock(),
                )
            except ConcurrentJobUpdateError:
                continue
            completed += 1
        return completed

    def close(self) -> None:
        self._repository.close()


def create_storage_cleaner(settings: Settings | None = None) -> StorageCleaner:
    selected = settings or Settings()
    if selected.job_backend != "postgres":
        raise RuntimeError("Storage cleaner requires the postgres job backend.")
    repository = SqlJobRepository.from_url(selected.database_url)
    if selected.auto_create_schema:
        repository.create_schema()
    return StorageCleaner(
        repository,
        WorkspaceManager(selected.storage_root),
        owner=f"cleanup-{os.getpid()}-{uuid4().hex[:12]}",
        clock=_utc_now,
        lease_seconds=selected.cleanup_lease_seconds,
        batch_size=selected.cleanup_batch_size,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    cleaner = create_storage_cleaner(settings)
    stop_event = Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        while not stop_event.is_set():
            completed = cleaner.run_once()
            if completed:
                LOGGER.info("Deleted %d expired job workspaces", completed)
                continue
            stop_event.wait(settings.cleanup_poll_interval_seconds)
    finally:
        cleaner.close()


def _utc_now() -> datetime:
    return datetime.now(UTC)
