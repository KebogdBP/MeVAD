"""Standalone PostgreSQL-to-Redis outbox relay."""

import logging
import os
import signal
from datetime import UTC, datetime
from threading import Event
from uuid import uuid4

from mevad.jobs import OutboxRelay
from mevad.jobs.redis_queue import RedisJobQueue
from mevad.jobs.sql_repository import SqlJobRepository
from mevad_api.config import Settings

LOGGER = logging.getLogger("mevad.outbox")


def create_outbox_relay(settings: Settings | None = None) -> OutboxRelay:
    """Compose the production outbox relay."""

    selected = settings or Settings()
    if selected.job_backend != "postgres" or selected.queue_backend != "redis":
        raise RuntimeError("Outbox relay requires postgres and redis backends.")
    repository = SqlJobRepository.from_url(selected.database_url)
    if selected.auto_create_schema:
        repository.create_schema()
    queue = RedisJobQueue.from_url(
        selected.redis_url,
        queue_name=selected.redis_queue_name,
    )
    owner = f"outbox-{os.getpid()}-{uuid4().hex[:12]}"
    return OutboxRelay(
        repository,
        queue,
        owner=owner,
        clock=_utc_now,
        lease_seconds=selected.outbox_lease_seconds,
        batch_size=selected.outbox_batch_size,
    )


def main() -> None:
    """Relay outbox events until SIGINT or SIGTERM."""

    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    relay = create_outbox_relay(settings)
    stop_event = Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        while not stop_event.is_set():
            published = relay.run_once()
            if published:
                LOGGER.info("Published %d outbox events", published)
                continue
            stop_event.wait(settings.outbox_poll_interval_seconds)
    finally:
        relay.close()


def _utc_now() -> datetime:
    return datetime.now(UTC)
