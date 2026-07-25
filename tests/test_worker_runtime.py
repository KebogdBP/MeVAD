from datetime import UTC, datetime

from mevad.jobs import (
    InMemoryJobQueue,
    InMemoryJobRepository,
    Job,
    JobOperation,
    JobService,
    JobStatus,
)
from mevad_worker.runtime import WorkerRuntime


class FakeExecutor:
    def __init__(self, result: Job) -> None:
        self.result = result
        self.calls: list[str] = []

    def execute(self, job_id: str) -> Job:
        self.calls.append(job_id)
        return self.result


class RecordingQueue(InMemoryJobQueue):
    def __init__(self) -> None:
        super().__init__()
        self.acknowledged: list[str] = []

    def acknowledge(self, job_id: str) -> None:
        self.acknowledged.append(job_id)


def test_worker_runtime_executes_and_acknowledges() -> None:
    queue = RecordingQueue()
    queue.enqueue("job-1")
    executor = FakeExecutor(_job())
    runtime = WorkerRuntime(
        queue,
        JobService(InMemoryJobRepository()),
        executor,
        poll_timeout_seconds=1,
    )

    assert runtime.run_once()
    assert executor.calls == ["job-1"]
    assert queue.acknowledged == ["job-1"]


def test_worker_runtime_reports_empty_poll() -> None:
    runtime = WorkerRuntime(
        InMemoryJobQueue(),
        JobService(InMemoryJobRepository()),
        FakeExecutor(_job()),
        poll_timeout_seconds=0,
    )

    assert not runtime.run_once()


def test_worker_runtime_requeues_failed_job_with_attempts_remaining() -> None:
    repository = InMemoryJobRepository()
    service = JobService(repository, job_id_factory=lambda: "job-1")
    service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    service.start("job-1")
    failed = service.fail(
        "job-1",
        error_code="job_execution_failed",
        error_message="The media job could not be completed.",
    )
    queue = InMemoryJobQueue()
    queue.enqueue("job-1")
    runtime = WorkerRuntime(queue, service, FakeExecutor(failed), poll_timeout_seconds=0)

    assert runtime.run_once()
    assert service.get("job-1").status is JobStatus.QUEUED
    assert queue.dequeue(timeout_seconds=0) == "job-1"


def test_worker_runtime_dead_letters_exhausted_job() -> None:
    repository = InMemoryJobRepository()
    exhausted = Job(
        job_id="job-1",
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
        status=JobStatus.FAILED,
        progress_percent=90,
        created_at=datetime(2026, 7, 25, tzinfo=UTC),
        updated_at=datetime(2026, 7, 25, tzinfo=UTC),
        version=7,
        attempt_count=3,
        max_attempts=3,
        error_code="job_execution_failed",
        error_message="The media job could not be completed.",
    )
    repository.add(exhausted)
    service = JobService(repository)
    queue = InMemoryJobQueue()
    queue.enqueue("job-1")
    runtime = WorkerRuntime(
        queue,
        service,
        FakeExecutor(exhausted),
        poll_timeout_seconds=0,
    )

    assert runtime.run_once()
    assert queue.dead_letters == ("job-1",)
    assert service.get("job-1").status is JobStatus.FAILED


def _job() -> Job:
    now = datetime(2026, 7, 25, tzinfo=UTC)
    return Job(
        job_id="job-1",
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
        status=JobStatus.SUCCEEDED,
        progress_percent=100,
        created_at=now,
        updated_at=now,
        version=3,
        result_reference="storage/jobs/job-1/results/video.mp4",
    )
