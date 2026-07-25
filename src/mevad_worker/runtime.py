"""Long-running Redis/PostgreSQL worker process."""

import logging
import signal
from collections.abc import Callable
from threading import Event
from typing import Protocol

from mevad.exceptions import InvalidJobTransitionError, JobNotFoundError
from mevad.jobs import Job, JobQueue, JobService
from mevad.jobs.redis_queue import RedisJobQueue
from mevad.jobs.sql_repository import SqlJobRepository
from mevad_api.config import Settings
from mevad_worker.factory import create_default_executor

LOGGER = logging.getLogger("mevad.worker")


class JobRunner(Protocol):
    def execute(self, job_id: str) -> Job:
        """Execute one claimed job."""
        ...


class WorkerRuntime:
    """Claim queued identifiers and execute them until shutdown."""

    def __init__(
        self,
        queue: JobQueue,
        executor: JobRunner,
        *,
        poll_timeout_seconds: int = 5,
    ) -> None:
        self._queue = queue
        self._executor = executor
        self._poll_timeout_seconds = poll_timeout_seconds

    def recover(self) -> int:
        return self._queue.recover_inflight()

    def run_once(self) -> bool:
        job_id = self._queue.dequeue(timeout_seconds=self._poll_timeout_seconds)
        if job_id is None:
            return False
        try:
            self._executor.execute(job_id)
        except (InvalidJobTransitionError, JobNotFoundError):
            LOGGER.warning("Discarding stale queue entry for job %s", job_id)
        self._queue.acknowledge(job_id)
        return True

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
    service = JobService(repository)
    return WorkerRuntime(
        queue,
        create_default_executor(service, storage_root=selected.storage_root),
        poll_timeout_seconds=selected.worker_poll_timeout_seconds,
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
