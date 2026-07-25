from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from mevad.exceptions import ConcurrentJobUpdateError, JobQueueError
from mevad.jobs import (
    InMemoryJobQueue,
    Job,
    JobClaim,
    JobOperation,
    JobService,
    JobStatus,
    OutboxRelay,
    SqlJobOutbox,
)
from mevad.jobs.redis_queue import RedisJobQueue
from mevad.jobs.sql_repository import SqlJobRepository


class FakeRedis:
    def __init__(self) -> None:
        self.ready: list[bytes] = []
        self.processing: list[bytes] = []
        self.dead: list[bytes] = []
        self.delayed: dict[bytes, float] = {}
        self.fail = False

    def lpush(self, name: str, *values: str) -> int:
        self._check()
        assert name == "test:jobs"
        self.ready[0:0] = [value.encode() for value in values]
        return len(self.ready)

    def brpoplpush(self, src: str, dst: str, timeout: int = 0) -> bytes | None:
        self._check()
        assert (src, dst) == ("test:jobs", "test:jobs:processing")
        if not self.ready:
            return None
        value = self.ready.pop()
        self.processing.insert(0, value)
        return value

    def lrem(self, name: str, count: int, value: str) -> int:
        self._check()
        assert (name, count) == ("test:jobs:processing", 1)
        encoded = value.encode()
        if encoded not in self.processing:
            return 0
        self.processing.remove(encoded)
        return 1

    def llen(self, name: str) -> int:
        self._check()
        assert name == "test:jobs:processing"
        return len(self.processing)

    def rpoplpush(self, src: str, dst: str) -> bytes | None:
        self._check()
        assert (src, dst) == ("test:jobs:processing", "test:jobs")
        if not self.processing:
            return None
        value = self.processing.pop()
        self.ready.insert(0, value)
        return value

    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> object:
        self._check()
        assert script
        if "ZRANGEBYSCORE" in script:
            delayed, ready, now, limit = keys_and_args
            assert (delayed, ready) == ("test:jobs:delayed", "test:jobs")
            due = [payload for payload, score in self.delayed.items() if score <= float(now)][
                : int(limit)
            ]
            for payload in due:
                del self.delayed[payload]
                self.ready.insert(0, payload)
            return len(due)
        if "ZADD" in script:
            source, delayed, receipt, score, replacement = keys_and_args
            assert (source, delayed) == (
                "test:jobs:processing",
                "test:jobs:delayed",
            )
            encoded = receipt.encode()
            if encoded not in self.processing:
                return 0
            self.processing.remove(encoded)
            self.delayed[replacement.encode()] = float(score)
            return 1
        if numkeys == 1:
            source, receipt, replacement = keys_and_args
            assert source == "test:jobs:processing"
            encoded = receipt.encode()
            if encoded not in self.processing:
                return 0
            self.processing.remove(encoded)
            self.processing.insert(0, replacement.encode())
            return 1
        assert numkeys == 2
        source, destination, receipt, replacement = keys_and_args
        assert source == "test:jobs:processing"
        encoded = receipt.encode()
        if encoded not in self.processing:
            return 0
        self.processing.remove(encoded)
        target = self.ready if destination == "test:jobs" else self.dead
        target.insert(0, replacement.encode())
        return 1

    def lrange(self, name: str, start: int, end: int) -> list[bytes]:
        self._check()
        assert (name, start, end) == ("test:jobs:processing", 0, -1)
        return list(self.processing)

    def _check(self) -> None:
        if self.fail:
            from redis.exceptions import ConnectionError

            raise ConnectionError("redis unavailable")


def test_sql_repository_round_trip_and_optimistic_update(
    sql_repository: SqlJobRepository,
) -> None:
    repository = sql_repository
    job = _job()

    repository.add(job)
    persisted = repository.get(job.job_id)

    assert persisted == job
    assert persisted is not None
    assert persisted.parameters == {"quality": "720p"}

    updated = replace(job, status=JobStatus.RUNNING, version=2)
    repository.update(updated, expected_version=1)
    assert repository.get(job.job_id) == updated

    with pytest.raises(ConcurrentJobUpdateError):
        repository.update(replace(updated, version=3), expected_version=1)


def test_sql_repository_finds_expired_leases(
    sql_repository: SqlJobRepository,
) -> None:
    job = replace(
        _job(),
        status=JobStatus.RUNNING,
        lease_owner="worker-1",
        lease_expires_at=datetime(2026, 7, 25, 12, 1, tzinfo=UTC),
    )
    sql_repository.add(job)

    expired = sql_repository.find_expired(
        now=datetime(2026, 7, 25, 12, 2, tzinfo=UTC),
        limit=10,
    )

    assert expired == (job,)


def test_sql_repository_rejects_duplicate_identifier(
    sql_repository: SqlJobRepository,
) -> None:
    repository = sql_repository
    repository.add(_job())

    with pytest.raises(ConcurrentJobUpdateError):
        repository.add(_job())


def test_redis_queue_claim_acknowledge_and_recovery() -> None:
    client = FakeRedis()
    receipts = iter(("delivery-1", "delivery-2"))
    queue = RedisJobQueue(
        client,
        queue_name="test:jobs",
        receipt_factory=lambda: next(receipts),
    )

    queue.enqueue("job-1")
    queue.enqueue("job-2")

    first = queue.dequeue(timeout_seconds=1)
    assert first is not None and first.job_id == "job-1"
    queue.acknowledge(first)
    second = queue.dequeue(timeout_seconds=1)
    assert second is not None and second.job_id == "job-2"
    assert queue.recover_inflight() == 1
    recovered = queue.dequeue(timeout_seconds=1)
    assert recovered is not None
    assert recovered.job_id == second.job_id
    assert recovered.receipt != second.receipt
    assert recovered.claimed_at is not None


def test_redis_queue_retries_and_dead_letters_claims() -> None:
    client = FakeRedis()
    receipts = iter(("retry-delivery", "dead-delivery", "retry-delivery-2"))
    queue = RedisJobQueue(
        client,
        queue_name="test:jobs",
        receipt_factory=lambda: next(receipts),
    )
    queue.enqueue("retry-job")
    queue.enqueue("dead-job")

    retry_claim = queue.dequeue(timeout_seconds=1)
    assert retry_claim is not None and retry_claim.job_id == "retry-job"
    queue.retry(retry_claim)
    dead_claim = queue.dequeue(timeout_seconds=1)
    assert dead_claim is not None and dead_claim.job_id == "dead-job"
    queue.dead_letter(dead_claim)

    retried = queue.dequeue(timeout_seconds=1)
    assert retried is not None
    assert retried.job_id == retry_claim.job_id
    assert retried.receipt != retry_claim.receipt
    assert client.dead == [dead_claim.receipt.encode()]
    queue.acknowledge(retried)


def test_redis_queue_promotes_delayed_retry_when_due() -> None:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    current = now
    client = FakeRedis()
    queue = RedisJobQueue(
        client,
        queue_name="test:jobs",
        clock=lambda: current,
    )
    queue.enqueue("job-1")
    claim = queue.dequeue(timeout_seconds=1)
    assert claim is not None

    queue.retry(claim, delay_seconds=5)
    assert queue.dequeue(timeout_seconds=0) is None

    current += timedelta(seconds=5)
    retried = queue.dequeue(timeout_seconds=0)
    assert retried is not None and retried.job_id == "job-1"
    assert retried.receipt != claim.receipt


def test_redis_queue_stale_receipt_cannot_acknowledge_retry() -> None:
    client = FakeRedis()
    receipts = iter(("delivery-1", "delivery-2"))
    queue = RedisJobQueue(
        client,
        queue_name="test:jobs",
        receipt_factory=lambda: next(receipts),
    )
    queue.enqueue("job-1")
    original = queue.dequeue(timeout_seconds=1)
    assert original is not None
    queue.retry(original)
    retried = queue.dequeue(timeout_seconds=1)
    assert retried is not None and retried.receipt != original.receipt

    with pytest.raises(JobQueueError, match="not found"):
        queue.acknowledge(original)

    queue.acknowledge(retried)


def test_redis_queue_reads_legacy_plain_job_identifier() -> None:
    client = FakeRedis()
    client.ready.append(b"legacy-job")
    queue = RedisJobQueue(client, queue_name="test:jobs")

    claim = queue.dequeue(timeout_seconds=1)

    assert claim is not None and claim.job_id == "legacy-job"
    assert claim.claimed_at is not None
    queue.acknowledge(claim)


def test_redis_queue_finds_only_claims_before_deadline() -> None:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    queue = RedisJobQueue(
        FakeRedis(),
        queue_name="test:jobs",
        clock=lambda: now,
    )
    queue.enqueue("job-1")
    claim = queue.dequeue(timeout_seconds=1)
    assert claim is not None

    assert queue.find_stale(before=now - timedelta(seconds=1)) == ()
    assert queue.find_stale(before=now) == (claim,)


def test_redis_queue_maps_connection_errors() -> None:
    client = FakeRedis()
    client.fail = True
    queue = RedisJobQueue(client, queue_name="test:jobs")

    with pytest.raises(JobQueueError):
        queue.enqueue("job-1")
    with pytest.raises(JobQueueError):
        queue.dequeue(timeout_seconds=1)
    with pytest.raises(JobQueueError):
        queue.recover_inflight()
    with pytest.raises(JobQueueError):
        queue.find_stale(before=datetime.now(UTC))
    with pytest.raises(JobQueueError):
        queue.retry(JobClaim(job_id="job-1", receipt="receipt"))
    with pytest.raises(JobQueueError):
        queue.dead_letter(JobClaim(job_id="job-1", receipt="receipt"))


def test_service_publishes_created_job(sql_repository: SqlJobRepository) -> None:
    queue = InMemoryJobQueue()
    service = JobService(sql_repository, queue=queue, job_id_factory=lambda: "job-1")

    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "720p"},
    )

    claim = queue.dequeue(timeout_seconds=0)
    assert claim is not None and claim.job_id == "job-1"


class FailingQueue(InMemoryJobQueue):
    def enqueue(self, job_id: str) -> None:
        raise JobQueueError("offline")


def test_service_marks_job_failed_when_publish_fails(
    sql_repository: SqlJobRepository,
) -> None:
    service = JobService(
        sql_repository,
        queue=FailingQueue(),
        job_id_factory=lambda: "job-1",
    )

    with pytest.raises(JobQueueError):
        service.create(
            operation=JobOperation.DOWNLOAD_VIDEO,
            source_url="https://example.com/video",
            parameters={"quality": "720p"},
        )

    job = sql_repository.get("job-1")
    assert job is not None
    assert job.status is JobStatus.FAILED
    assert job.error_code == "job_enqueue_failed"


def test_sql_outbox_persists_job_and_event_atomically(
    sql_repository: SqlJobRepository,
) -> None:
    outbox = SqlJobOutbox(sql_repository, event_id_factory=lambda: "event-1")
    service = JobService(
        sql_repository,
        outbox=outbox,
        job_id_factory=iter(("job-1", "job-2")).__next__,
    )
    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "720p"},
    )

    with pytest.raises(ConcurrentJobUpdateError):
        service.create(
            operation=JobOperation.DOWNLOAD_VIDEO,
            source_url="https://example.com/other",
            parameters={"quality": "720p"},
        )

    assert sql_repository.get("job-1") is not None
    assert sql_repository.get("job-2") is None


def test_outbox_relay_publishes_and_marks_event(
    sql_repository: SqlJobRepository,
) -> None:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    outbox = SqlJobOutbox(sql_repository, event_id_factory=lambda: "event-1")
    service = JobService(
        sql_repository,
        outbox=outbox,
        job_id_factory=lambda: "job-1",
    )
    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "720p"},
    )
    queue = InMemoryJobQueue(clock=lambda: now)
    relay = OutboxRelay(
        sql_repository,
        queue,
        owner="relay-1",
        clock=lambda: now,
    )

    assert relay.run_once() == 1
    claim = queue.dequeue(timeout_seconds=0)
    assert claim is not None and claim.job_id == "job-1"
    assert relay.run_once() == 0


def test_outbox_relay_releases_event_after_queue_failure(
    sql_repository: SqlJobRepository,
) -> None:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    outbox = SqlJobOutbox(sql_repository, event_id_factory=lambda: "event-1")
    service = JobService(
        sql_repository,
        outbox=outbox,
        job_id_factory=lambda: "job-1",
    )
    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "720p"},
    )
    failing = OutboxRelay(
        sql_repository,
        FailingQueue(),
        owner="relay-1",
        clock=lambda: now,
    )

    assert failing.run_once() == 0
    events = sql_repository.claim_outbox(
        owner="relay-2",
        now=now,
        lease_seconds=30,
        limit=10,
    )
    assert len(events) == 1
    assert events[0].attempt_count == 2


def test_sql_outbox_recovers_expired_relay_lease(
    sql_repository: SqlJobRepository,
) -> None:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    service = JobService(
        sql_repository,
        outbox=SqlJobOutbox(sql_repository, event_id_factory=lambda: "event-1"),
        job_id_factory=lambda: "job-1",
    )
    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "720p"},
    )

    first = sql_repository.claim_outbox(
        owner="relay-1",
        now=now,
        lease_seconds=30,
        limit=10,
    )
    while_leased = sql_repository.claim_outbox(
        owner="relay-2",
        now=now + timedelta(seconds=29),
        lease_seconds=30,
        limit=10,
    )
    recovered = sql_repository.claim_outbox(
        owner="relay-2",
        now=now + timedelta(seconds=30),
        lease_seconds=30,
        limit=10,
    )

    assert len(first) == 1
    assert while_leased == ()
    assert len(recovered) == 1
    assert recovered[0].attempt_count == 2
    assert recovered[0].lease_owner == "relay-2"


def test_job_service_rejects_direct_queue_with_outbox(
    sql_repository: SqlJobRepository,
) -> None:
    with pytest.raises(ValueError, match="cannot use direct queue"):
        JobService(
            sql_repository,
            queue=InMemoryJobQueue(),
            outbox=SqlJobOutbox(sql_repository),
        )


@pytest.fixture
def sql_repository() -> Iterator[SqlJobRepository]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    repository = SqlJobRepository(engine)
    repository.create_schema()
    yield repository
    repository.close()


def _job() -> Job:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    return Job(
        job_id="job-1",
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "720p"},
        status=JobStatus.QUEUED,
        progress_percent=0,
        created_at=now,
        updated_at=now,
        version=1,
    )
