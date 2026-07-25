"""Redis-backed job queue adapter."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from mevad.exceptions import JobQueueError
from mevad.jobs.queue import JobClaim


class RedisListClient(Protocol):
    """Subset of redis-py used by the queue adapter."""

    def lpush(self, name: str, *values: str) -> int: ...

    def brpoplpush(self, src: str, dst: str, timeout: int = 0) -> bytes | None: ...

    def lrem(self, name: str, count: int, value: str) -> int: ...

    def llen(self, name: str) -> int: ...

    def rpoplpush(self, src: str, dst: str) -> bytes | None: ...

    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> object: ...

    def lrange(self, name: str, start: int, end: int) -> list[bytes]: ...


_MOVE_CLAIM_SCRIPT = """
local removed = redis.call('LREM', KEYS[1], 1, ARGV[1])
if removed == 1 then
    redis.call('LPUSH', KEYS[2], ARGV[2])
end
return removed
"""

_STAMP_CLAIM_SCRIPT = """
local removed = redis.call('LREM', KEYS[1], 1, ARGV[1])
if removed == 1 then
    redis.call('LPUSH', KEYS[1], ARGV[2])
end
return removed
"""


class RedisJobQueue:
    """FIFO queue built from Redis LPUSH/BRPOP."""

    def __init__(
        self,
        client: RedisListClient,
        *,
        queue_name: str = "mevad:jobs",
        receipt_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not queue_name:
            raise ValueError("Redis queue name cannot be empty.")
        self._client = client
        self._queue_name = queue_name
        self._processing_name = f"{queue_name}:processing"
        self._dead_letter_name = f"{queue_name}:dead"
        self._receipt_factory = receipt_factory or _new_receipt
        self._clock = clock or _utc_now

    @classmethod
    def from_url(cls, redis_url: str, *, queue_name: str = "mevad:jobs") -> "RedisJobQueue":
        client = cast(RedisListClient, Redis.from_url(redis_url, decode_responses=False))
        return cls(client, queue_name=queue_name)

    def enqueue(self, job_id: str) -> None:
        payload = self._new_payload(job_id)
        try:
            self._client.lpush(self._queue_name, payload)
        except RedisError as error:
            raise JobQueueError("Could not publish the job.") from error

    def dequeue(self, *, timeout_seconds: int) -> JobClaim | None:
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
            payload = item.decode("utf-8")
        except UnicodeDecodeError as error:
            raise JobQueueError("Queue payload is not valid UTF-8.") from error
        stamped = self._stamp_payload(payload)
        try:
            moved = self._client.eval(
                _STAMP_CLAIM_SCRIPT,
                1,
                self._processing_name,
                payload,
                stamped,
            )
        except RedisError as error:
            raise JobQueueError("Could not timestamp the claimed job.") from error
        if moved != 1:
            raise JobQueueError("Claimed job was not found in the processing queue.")
        return _decode_claim(stamped)

    def acknowledge(self, claim: JobClaim) -> None:
        try:
            removed = self._client.lrem(self._processing_name, 1, claim.receipt)
        except RedisError as error:
            raise JobQueueError("Could not acknowledge the job.") from error
        if removed != 1:
            raise JobQueueError("Claimed job was not found in the processing queue.")

    def retry(self, claim: JobClaim) -> None:
        self._move_claim(
            claim,
            self._queue_name,
            replacement=self._new_payload(claim.job_id),
            action="retry",
        )

    def dead_letter(self, claim: JobClaim) -> None:
        self._move_claim(
            claim,
            self._dead_letter_name,
            replacement=claim.receipt,
            action="dead-letter",
        )

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

    def find_stale(self, *, before: datetime) -> tuple[JobClaim, ...]:
        try:
            payloads = self._client.lrange(self._processing_name, 0, -1)
        except RedisError as error:
            raise JobQueueError("Could not inspect in-flight jobs.") from error
        claims: list[JobClaim] = []
        for raw in payloads:
            try:
                claim = _decode_claim(raw.decode("utf-8"))
            except UnicodeDecodeError as error:
                raise JobQueueError("Queue payload is not valid UTF-8.") from error
            if claim.claimed_at is not None and claim.claimed_at <= before:
                claims.append(claim)
        return tuple(claims)

    def _move_claim(
        self,
        claim: JobClaim,
        destination: str,
        *,
        replacement: str,
        action: str,
    ) -> None:
        try:
            moved = self._client.eval(
                _MOVE_CLAIM_SCRIPT,
                2,
                self._processing_name,
                destination,
                claim.receipt,
                replacement,
            )
        except RedisError as error:
            raise JobQueueError(f"Could not {action} the job.") from error
        if moved != 1:
            raise JobQueueError("Claimed job was not found in the processing queue.")

    def _new_payload(self, job_id: str) -> str:
        return json.dumps(
            {
                "delivery_id": self._receipt_factory(),
                "created_at": self._clock().timestamp(),
                "job_id": job_id,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    def _stamp_payload(self, payload: str) -> str:
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            decoded = {
                "created_at": self._clock().timestamp(),
                "delivery_id": self._receipt_factory(),
                "job_id": payload,
            }
        if not isinstance(decoded, dict):
            raise JobQueueError("Queue payload has an invalid structure.")
        decoded["claimed_at"] = self._clock().timestamp()
        return json.dumps(decoded, separators=(",", ":"), sort_keys=True)


def _decode_claim(payload: str) -> JobClaim:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return JobClaim(job_id=payload, receipt=payload)
    if not isinstance(decoded, dict):
        raise JobQueueError("Queue payload has an invalid structure.")
    job_id = decoded.get("job_id")
    delivery_id = decoded.get("delivery_id")
    if not isinstance(job_id, str) or not job_id:
        raise JobQueueError("Queue payload has no valid job identifier.")
    if not isinstance(delivery_id, str) or not delivery_id:
        raise JobQueueError("Queue payload has no valid delivery identifier.")
    timestamp = decoded.get("claimed_at", decoded.get("created_at"))
    claimed_at = (
        datetime.fromtimestamp(float(timestamp), tz=UTC)
        if isinstance(timestamp, int | float)
        else None
    )
    return JobClaim(job_id=job_id, receipt=payload, claimed_at=claimed_at)


def _new_receipt() -> str:
    return uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(UTC)
