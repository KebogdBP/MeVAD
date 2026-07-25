from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime

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
)
from mevad.jobs.redis_queue import RedisJobQueue
from mevad.jobs.sql_repository import SqlJobRepository


class FakeRedis:
    def __init__(self) -> None:
        self.ready: list[bytes] = []
        self.processing: list[bytes] = []
        self.dead: list[bytes] = []
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
    assert recovered == second


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

    assert claim == JobClaim(job_id="legacy-job", receipt="legacy-job")
    queue.acknowledge(claim)


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
