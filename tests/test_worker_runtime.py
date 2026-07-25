from datetime import UTC, datetime

from mevad.jobs import InMemoryJobQueue, Job, JobOperation, JobStatus
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
    runtime = WorkerRuntime(queue, executor, poll_timeout_seconds=1)

    assert runtime.run_once()
    assert executor.calls == ["job-1"]
    assert queue.acknowledged == ["job-1"]


def test_worker_runtime_reports_empty_poll() -> None:
    runtime = WorkerRuntime(
        InMemoryJobQueue(),
        FakeExecutor(_job()),
        poll_timeout_seconds=0,
    )

    assert not runtime.run_once()


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
