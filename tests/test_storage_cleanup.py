from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mevad.exceptions import ConcurrentJobUpdateError
from mevad.jobs import InMemoryJobRepository, JobOperation, JobService, JobStatus
from mevad_api.config import Settings
from mevad_worker.cleanup_runtime import StorageCleaner, create_storage_cleaner
from mevad_worker.storage import WorkspaceManager


def test_cleaner_deletes_terminal_workspace_only_after_ttl(tmp_path: Path) -> None:
    current = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    repository = InMemoryJobRepository()
    service = JobService(
        repository,
        clock=lambda: current,
        job_id_factory=lambda: "job-1",
        storage_retention_seconds=60,
    )
    job = service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    service.start(job.job_id)
    workspace = WorkspaceManager(tmp_path).prepare(job.job_id)
    output = workspace.results / "video.mp4"
    output.write_bytes(b"video")
    completed = service.succeed(
        job.job_id,
        result_reference="job-1/results/video.mp4",
    )
    cleaner = StorageCleaner(
        repository,
        WorkspaceManager(tmp_path),
        owner="cleanup-1",
        clock=lambda: current,
    )

    assert completed.result_expires_at == current + timedelta(seconds=60)
    current += timedelta(seconds=59)
    assert cleaner.run_once() == 0
    assert workspace.root.exists()

    current += timedelta(seconds=1)
    assert cleaner.run_once() == 1
    assert not workspace.root.exists()
    cleaned = service.get(job.job_id)
    assert cleaned.status is JobStatus.SUCCEEDED
    assert cleaned.result_reference is None
    assert cleaned.storage_deleted_at == current


def test_cleaner_never_claims_active_workspace(tmp_path: Path) -> None:
    current = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    repository = InMemoryJobRepository()
    service = JobService(
        repository,
        clock=lambda: current,
        job_id_factory=lambda: "job-1",
    )
    job = service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    workspace = WorkspaceManager(tmp_path).prepare(job.job_id)
    cleaner = StorageCleaner(
        repository,
        WorkspaceManager(tmp_path),
        owner="cleanup-1",
        clock=lambda: current,
    )

    current += timedelta(days=30)

    assert cleaner.run_once() == 0
    assert workspace.root.exists()
    assert service.get(job.job_id).status is JobStatus.QUEUED


def test_cleanup_lease_fences_retry_transition(tmp_path: Path) -> None:
    current = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    repository = InMemoryJobRepository()
    service = JobService(
        repository,
        clock=lambda: current,
        job_id_factory=lambda: "job-1",
        storage_retention_seconds=60,
    )
    job = service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    service.start(job.job_id)
    service.fail(
        job.job_id,
        error_code="job_execution_failed",
        error_message="The media job could not be completed.",
    )
    current += timedelta(seconds=60)

    claims = repository.claim_storage_cleanup(
        owner="cleanup-1",
        now=current,
        lease_seconds=300,
        limit=10,
    )

    assert len(claims) == 1
    with pytest.raises(ConcurrentJobUpdateError):
        service.retry(job.job_id)


def test_cleaner_refuses_symlinked_job_workspace(tmp_path: Path) -> None:
    current = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    outside = tmp_path / "outside"
    outside.mkdir()
    protected = outside / "keep.txt"
    protected.write_text("keep", encoding="utf-8")
    storage = tmp_path / "storage"
    storage.mkdir()
    try:
        (storage / "job-1").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires an unavailable platform privilege.")
    repository = InMemoryJobRepository()
    service = JobService(
        repository,
        clock=lambda: current,
        job_id_factory=lambda: "job-1",
        storage_retention_seconds=60,
    )
    job = service.create(
        operation=JobOperation.DOWNLOAD_VIDEO,
        source_url="https://example.com/video",
        parameters={"quality": "best"},
    )
    service.cancel(job.job_id)
    current += timedelta(seconds=60)
    cleaner = StorageCleaner(
        repository,
        WorkspaceManager(storage),
        owner="cleanup-1",
        clock=lambda: current,
    )

    assert cleaner.run_once() == 0
    assert protected.read_text(encoding="utf-8") == "keep"
    assert service.get(job.job_id).storage_deleted_at is None


def test_cleanup_runtime_requires_postgres() -> None:
    with pytest.raises(RuntimeError, match="requires the postgres"):
        create_storage_cleaner(
            Settings(
                job_backend="memory",
                require_media_tools=False,
            )
        )
