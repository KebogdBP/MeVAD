"""Immutable job domain models."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypeAlias

JobParameter: TypeAlias = str | int | float | bool


class JobOperation(StrEnum):
    """Background media operations supported by the API contract."""

    DOWNLOAD_VIDEO = "download_video"
    EXTRACT_AUDIO = "extract_audio"
    CUT_VIDEO = "cut_video"
    MAKE_LOOP = "make_loop"


class JobStatus(StrEnum):
    """Job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    PROCESSING = "processing"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }


@dataclass(frozen=True, slots=True)
class Job:
    """Persistable immutable background job."""

    job_id: str
    operation: JobOperation
    source_url: str
    parameters: Mapping[str, JobParameter]
    status: JobStatus
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    version: int
    attempt_count: int = 0
    max_attempts: int = 3
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    result_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None
