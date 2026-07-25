"""Shared safe subprocess boundary for local media tools."""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from mevad.exceptions import MediaProcessingError


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Captured external process result."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Injectable no-shell process runner."""

    def __call__(self, arguments: Sequence[str], *, timeout: float) -> ProcessResult:
        """Run one bounded external process."""
        ...


def run_process(arguments: Sequence[str], *, timeout: float) -> ProcessResult:
    """Run a process without a shell and capture bounded command output."""

    try:
        completed = subprocess.run(
            list(arguments),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        raise MediaProcessingError("Media tool timed out.") from error
    except OSError as error:
        raise MediaProcessingError(f"Media tool could not start: {error}") from error
    return ProcessResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def safe_process_error(stderr: str, *, prefix: str = "FFmpeg failed") -> str:
    """Return a short user-safe summary from process stderr."""

    last_line = next(
        (line.strip() for line in reversed(stderr.splitlines()) if line.strip()),
        "unknown media processing error",
    )
    return f"{prefix}: {last_line[:500]}"
