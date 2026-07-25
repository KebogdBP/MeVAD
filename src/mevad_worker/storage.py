"""Per-job filesystem workspace with path confinement."""

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from mevad.exceptions import MediaProcessingError

_SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


@dataclass(frozen=True, slots=True)
class JobWorkspace:
    """Directories owned by one job."""

    root: Path
    intermediate: Path
    results: Path


class WorkspaceManager:
    """Create and clean isolated job directories under one storage root."""

    def __init__(self, storage_root: Path) -> None:
        self._storage_root = storage_root.expanduser().resolve()

    def prepare(self, job_id: str) -> JobWorkspace:
        if _SAFE_JOB_ID.fullmatch(job_id) is None:
            raise MediaProcessingError("Job identifier is not safe for filesystem storage.")

        root = (self._storage_root / job_id).resolve()
        self._ensure_contained(root)
        intermediate = root / "intermediate"
        results = root / "results"
        intermediate.mkdir(parents=True, exist_ok=True)
        results.mkdir(parents=True, exist_ok=True)
        self._ensure_directory(intermediate)
        self._ensure_directory(results)
        return JobWorkspace(
            root=root,
            intermediate=intermediate,
            results=results,
        )

    def result_reference(self, output_path: Path) -> str:
        resolved = output_path.expanduser().resolve()
        self._ensure_contained(resolved)
        if not resolved.is_file():
            raise MediaProcessingError("Worker result file was not found.")
        return resolved.relative_to(self._storage_root).as_posix()

    def cleanup_intermediate(self, workspace: JobWorkspace) -> None:
        self._ensure_directory(workspace.intermediate)
        if workspace.intermediate.exists():
            shutil.rmtree(workspace.intermediate)

    def cleanup_job(self, job_id: str) -> None:
        """Remove one complete job workspace without following symlinks."""

        if _SAFE_JOB_ID.fullmatch(job_id) is None:
            raise MediaProcessingError("Job identifier is not safe for filesystem storage.")
        root = self._storage_root / job_id
        if root.is_symlink():
            raise MediaProcessingError("Job workspace must not be a symbolic link.")
        self._ensure_contained(root.resolve())
        if not root.exists():
            return
        self._ensure_directory(root)
        shutil.rmtree(root)

    def _ensure_contained(self, path: Path) -> None:
        if path == self._storage_root or not path.is_relative_to(self._storage_root):
            raise MediaProcessingError("Job workspace path escapes the storage root.")

    def _ensure_directory(self, path: Path) -> None:
        if path.is_symlink():
            raise MediaProcessingError("Job workspace directories must not be symbolic links.")
        resolved = path.resolve()
        self._ensure_contained(resolved)
        if not resolved.is_dir():
            raise MediaProcessingError("Job workspace path is not a directory.")
