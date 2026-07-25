"""Shared safe subprocess boundary for local media tools."""

import os
import signal
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from mevad.downloader import CancellationToken
from mevad.exceptions import (
    DownloadCancelledError,
    MediaProcessingError,
    MediaProcessTimeoutError,
)

PollCallback = Callable[[], None]


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Captured external process result."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Injectable no-shell process runner."""

    def __call__(
        self,
        arguments: Sequence[str],
        *,
        timeout: float,
        cancellation: CancellationToken | None = None,
        on_poll: PollCallback | None = None,
    ) -> ProcessResult:
        """Run one bounded external process."""
        ...


def run_process(
    arguments: Sequence[str],
    *,
    timeout: float,
    cancellation: CancellationToken | None = None,
    on_poll: PollCallback | None = None,
) -> ProcessResult:
    """Run a managed no-shell process with cancellation and hard timeout."""

    if timeout <= 0:
        raise ValueError("Process timeout must be positive.")
    if not arguments:
        raise ValueError("Process arguments cannot be empty.")
    if cancellation is not None and cancellation.is_cancelled:
        raise DownloadCancelledError("Media operation was cancelled.")
    try:
        process = subprocess.Popen(
            list(arguments),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            start_new_session=True,
        )
    except OSError as error:
        raise MediaProcessingError(f"Media tool could not start: {error}") from error

    try:
        deadline = monotonic() + timeout
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                _terminate(process)
                raise MediaProcessTimeoutError("Media tool timed out.")
            try:
                stdout, stderr = process.communicate(timeout=min(0.25, remaining))
                break
            except subprocess.TimeoutExpired:
                if cancellation is not None and cancellation.is_cancelled:
                    _terminate(process)
                    raise DownloadCancelledError("Media operation was cancelled.") from None
                if on_poll is not None:
                    on_poll()
    except (DownloadCancelledError, MediaProcessTimeoutError):
        raise
    except BaseException:
        _terminate(process)
        raise

    return ProcessResult(
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.communicate(timeout=2)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.communicate(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        process.kill()
        process.wait()


def safe_process_error(stderr: str, *, prefix: str = "FFmpeg failed") -> str:
    """Return a short user-safe summary from process stderr."""

    last_line = next(
        (line.strip() for line in reversed(stderr.splitlines()) if line.strip()),
        "unknown media processing error",
    )
    return f"{prefix}: {last_line[:500]}"
