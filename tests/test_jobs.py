from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from mevad.exceptions import (
    ConcurrentJobUpdateError,
    InvalidJobTransitionError,
    JobNotFoundError,
)
from mevad.jobs import InMemoryJobRepository, Job, JobOperation, JobService, JobStatus


class Clock:
    def __init__(self) -> None:
        self.current = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def test_creates_normalized_immutable_job() -> None:
    service = _service()

    job = service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url=" https://EXAMPLE.com/video#fragment ",
        parameters={"quality": "720p", "overwrite": False},
    )

    assert job.job_id == "job-1"
    assert job.source_url == "https://example.com/video"
    assert job.status is JobStatus.QUEUED
    assert job.progress_percent == 0
    assert job.version == 1
    assert job.parameters == {"quality": "720p", "overwrite": False}


def test_runs_processes_and_completes_job() -> None:
    service = _service()
    created = _create(service)

    running = service.start(created.job_id)
    progressed = service.report_progress(created.job_id, 25)
    processing = service.mark_processing(created.job_id)
    nearly_done = service.report_progress(created.job_id, 90)
    completed = service.succeed(
        created.job_id,
        result_reference="storage/jobs/job-1/video.mp4",
    )

    assert running.status is JobStatus.RUNNING
    assert running.attempt_count == 1
    assert progressed.progress_percent == 25
    assert processing.status is JobStatus.PROCESSING
    assert nearly_done.progress_percent == 90
    assert completed.status is JobStatus.SUCCEEDED
    assert completed.progress_percent == 100
    assert completed.result_reference == "storage/jobs/job-1/video.mp4"
    assert completed.version == 6


def test_cancels_queued_job_immediately() -> None:
    service = _service()
    job = _create(service)

    cancelled = service.cancel(job.job_id)

    assert cancelled.status is JobStatus.CANCELLED
    assert cancelled.status.is_terminal


def test_running_job_requires_worker_cancellation_acknowledgement() -> None:
    service = _service()
    job = _create(service)
    service.start(job.job_id)

    requested = service.cancel(job.job_id)
    cancelled = service.acknowledge_cancellation(job.job_id)

    assert requested.status is JobStatus.CANCEL_REQUESTED
    assert not requested.status.is_terminal
    assert cancelled.status is JobStatus.CANCELLED


def test_worker_can_fail_after_cancellation_request() -> None:
    service = _service()
    job = _create(service)
    service.start(job.job_id)
    service.cancel(job.job_id)

    failed = service.fail(
        job.job_id,
        error_code="worker_terminated",
        error_message="Worker stopped before cancellation acknowledgement.",
    )

    assert failed.status is JobStatus.FAILED
    assert failed.error_code == "worker_terminated"


def test_failed_job_can_retry_until_attempt_limit() -> None:
    service = _service()
    job = _create(service)
    service.start(job.job_id)
    service.fail(job.job_id, error_code="temporary", error_message="Temporary failure.")

    retried = service.retry(job.job_id)
    second_attempt = service.start(job.job_id)

    assert retried.status is JobStatus.QUEUED
    assert retried.progress_percent == 0
    assert retried.error_code is None
    assert second_attempt.attempt_count == 2

    service.fail(job.job_id, error_code="temporary", error_message="Temporary failure.")
    service.retry(job.job_id)
    service.start(job.job_id)
    service.fail(job.job_id, error_code="temporary", error_message="Temporary failure.")

    with pytest.raises(InvalidJobTransitionError, match="exhausted"):
        service.retry(job.job_id)


def test_rejects_decreasing_or_complete_progress() -> None:
    service = _service()
    job = _create(service)
    service.start(job.job_id)
    service.report_progress(job.job_id, 50)

    with pytest.raises(InvalidJobTransitionError):
        service.report_progress(job.job_id, 49)
    with pytest.raises(InvalidJobTransitionError):
        service.report_progress(job.job_id, 100)


def test_rejects_invalid_terminal_transition() -> None:
    service = _service()
    job = _create(service)
    service.cancel(job.job_id)

    with pytest.raises(InvalidJobTransitionError, match="Cannot cancel"):
        service.cancel(job.job_id)
    with pytest.raises(InvalidJobTransitionError, match="Expected queued"):
        service.start(job.job_id)


def test_missing_job_is_explicit() -> None:
    with pytest.raises(JobNotFoundError):
        _service().get("missing")


def test_repository_detects_optimistic_concurrency_conflict() -> None:
    repository = InMemoryJobRepository()
    service = JobService(
        repository,
        clock=Clock(),
        job_id_factory=lambda: "job-1",
    )
    job = _create(service)

    with pytest.raises(ConcurrentJobUpdateError):
        repository.update(
            replace(job, version=2),
            expected_version=999,
        )


def _service() -> JobService:
    return JobService(
        InMemoryJobRepository(),
        clock=Clock(),
        job_id_factory=lambda: "job-1",
    )


def _create(service: JobService) -> Job:
    return service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
