"""SQLAlchemy-backed durable job repository."""

from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from mevad.exceptions import ConcurrentJobUpdateError
from mevad.jobs.models import Job, JobOperation, JobStatus

metadata = MetaData()

jobs_table = Table(
    "jobs",
    metadata,
    Column("job_id", String(64), primary_key=True),
    Column("operation", String(32), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("parameters", JSON, nullable=False),
    Column("status", String(32), nullable=False, index=True),
    Column("progress_percent", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("version", Integer, nullable=False),
    Column("attempt_count", Integer, nullable=False),
    Column("max_attempts", Integer, nullable=False),
    Column("lease_owner", String(128)),
    Column("lease_expires_at", DateTime(timezone=True), index=True),
    Column("result_reference", Text),
    Column("error_code", String(64)),
    Column("error_message", Text),
)


class SqlJobRepository:
    """Persist jobs transactionally with optimistic version checks."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_url(cls, database_url: str) -> "SqlJobRepository":
        return cls(create_engine(database_url, pool_pre_ping=True))

    def create_schema(self) -> None:
        """Create tables for development and tests."""

        metadata.create_all(self._engine)

    def close(self) -> None:
        """Dispose pooled database connections owned by this repository."""

        self._engine.dispose()

    def add(self, job: Job) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(insert(jobs_table).values(**_to_record(job)))
        except IntegrityError as error:
            raise ConcurrentJobUpdateError("Job identifier already exists.") from error

    def get(self, job_id: str) -> Job | None:
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(jobs_table).where(jobs_table.c.job_id == job_id))
                .mappings()
                .one_or_none()
            )
        return _from_record(dict(row)) if row is not None else None

    def update(self, job: Job, *, expected_version: int) -> None:
        with self._engine.begin() as connection:
            result = connection.execute(
                update(jobs_table)
                .where(
                    jobs_table.c.job_id == job.job_id,
                    jobs_table.c.version == expected_version,
                )
                .values(**_to_record(job))
            )
            if result.rowcount != 1:
                raise ConcurrentJobUpdateError("Job was updated concurrently.")

    def find_expired(self, *, now: datetime, limit: int) -> tuple[Job, ...]:
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(jobs_table)
                    .where(
                        jobs_table.c.lease_expires_at.is_not(None),
                        jobs_table.c.lease_expires_at <= now,
                        jobs_table.c.status.not_in(
                            [
                                JobStatus.SUCCEEDED.value,
                                JobStatus.FAILED.value,
                                JobStatus.CANCELLED.value,
                            ]
                        ),
                    )
                    .order_by(jobs_table.c.lease_expires_at)
                    .limit(limit)
                )
                .mappings()
                .all()
            )
        return tuple(_from_record(dict(row)) for row in rows)


def _to_record(job: Job) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "operation": job.operation.value,
        "source_url": job.source_url,
        "parameters": dict(job.parameters),
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "version": job.version,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "lease_owner": job.lease_owner,
        "lease_expires_at": job.lease_expires_at,
        "result_reference": job.result_reference,
        "error_code": job.error_code,
        "error_message": job.error_message,
    }


def _from_record(record: dict[str, Any]) -> Job:
    parameters = {str(key): value for key, value in dict(record["parameters"]).items()}
    created_at = _as_utc(record["created_at"])
    updated_at = _as_utc(record["updated_at"])
    return Job(
        job_id=str(record["job_id"]),
        operation=JobOperation(str(record["operation"])),
        source_url=str(record["source_url"]),
        parameters=MappingProxyType(parameters),
        status=JobStatus(str(record["status"])),
        progress_percent=int(record["progress_percent"]),
        created_at=created_at,
        updated_at=updated_at,
        version=int(record["version"]),
        attempt_count=int(record["attempt_count"]),
        max_attempts=int(record["max_attempts"]),
        lease_owner=_optional_string(record["lease_owner"]),
        lease_expires_at=(
            _as_utc(record["lease_expires_at"]) if record["lease_expires_at"] is not None else None
        ),
        result_reference=_optional_string(record["result_reference"]),
        error_code=_optional_string(record["error_code"]),
        error_message=_optional_string(record["error_message"]),
    )


def _as_utc(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("Persisted job timestamp must be a datetime.")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)
