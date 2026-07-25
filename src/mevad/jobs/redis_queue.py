"""Redis-backed job queue adapter."""

from typing import Protocol, cast

from redis import Redis
from redis.exceptions import RedisError

from mevad.exceptions import JobQueueError


class RedisListClient(Protocol):
    """Subset of redis-py used by the queue adapter."""

    def lpush(self, name: str, *values: str) -> int: ...

    def brpoplpush(self, src: str, dst: str, timeout: int = 0) -> bytes | None: ...

    def lrem(self, name: str, count: int, value: str) -> int: ...

    def llen(self, name: str) -> int: ...

    def rpoplpush(self, src: str, dst: str) -> bytes | None: ...


class RedisJobQueue:
    """FIFO queue built from Redis LPUSH/BRPOP."""

    def __init__(self, client: RedisListClient, *, queue_name: str = "mevad:jobs") -> None:
        if not queue_name:
            raise ValueError("Redis queue name cannot be empty.")
        self._client = client
        self._queue_name = queue_name
        self._processing_name = f"{queue_name}:processing"

    @classmethod
    def from_url(cls, redis_url: str, *, queue_name: str = "mevad:jobs") -> "RedisJobQueue":
        client = cast(RedisListClient, Redis.from_url(redis_url, decode_responses=False))
        return cls(client, queue_name=queue_name)

    def enqueue(self, job_id: str) -> None:
        try:
            self._client.lpush(self._queue_name, job_id)
        except RedisError as error:
            raise JobQueueError("Could not publish the job.") from error

    def dequeue(self, *, timeout_seconds: int) -> str | None:
        if timeout_seconds < 0:
            raise ValueError("Queue timeout cannot be negative.")
        try:
            item = self._client.brpoplpush(
                self._queue_name,
                self._processing_name,
                timeout=timeout_seconds,
            )
        except RedisError as error:
            raise JobQueueError("Could not claim a job.") from error
        if item is None:
            return None
        try:
            return item.decode("utf-8")
        except UnicodeDecodeError as error:
            raise JobQueueError("Queue payload is not valid UTF-8.") from error

    def acknowledge(self, job_id: str) -> None:
        try:
            removed = self._client.lrem(self._processing_name, 1, job_id)
        except RedisError as error:
            raise JobQueueError("Could not acknowledge the job.") from error
        if removed != 1:
            raise JobQueueError("Claimed job was not found in the processing queue.")

    def recover_inflight(self) -> int:
        try:
            count = self._client.llen(self._processing_name)
            recovered = 0
            for _ in range(count):
                if self._client.rpoplpush(self._processing_name, self._queue_name) is not None:
                    recovered += 1
            return recovered
        except RedisError as error:
            raise JobQueueError("Could not recover in-flight jobs.") from error
