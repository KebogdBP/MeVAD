"""Shared safe subprocess boundary for local media tools."""

import os
import signal
import subprocess
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import Protocol, TextIO

from mevad.downloader import CancellationToken
from mevad.exceptions import (
    DownloadCancelledError,
    MediaProcessingError,
    MediaProcessTimeoutError,
)

PollCallback = Callable[[], None]
LineCallback = Callable[[str], None]
_MAX_CAPTURE_CHARS = 1_000_000
_MAX_LINE_CHARS = 65_536


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Captured external process result."""

    returncode: int
    stdout: str
    stderr: str


class _BoundedCapture:
    def __init__(self) -> None:
        self._chunks: deque[str] = deque()
        self._characters = 0

    def append(self, chunk: str) -> None:
        self._chunks.append(chunk)
        self._characters += len(chunk)
        while self._characters > _MAX_CAPTURE_CHARS and self._chunks:
            removed = self._chunks.popleft()
            self._characters -= len(removed)

    def render(self) -> str:
        return "".join(self._chunks)[-_MAX_CAPTURE_CHARS:]


class ProcessRunner(Protocol):
    """Injectable no-shell process runner."""

    def __call__(
        self,
        arguments: Sequence[str],
        *,
        timeout: float,
        cancellation: CancellationToken | None = None,
        on_poll: PollCallback | None = None,
        on_stdout_line: LineCallback | None = None,
    ) -> ProcessResult:
        """Run one bounded external process."""
        ...


def run_process(
    arguments: Sequence[str],
    *,
    timeout: float,
    cancellation: CancellationToken | None = None,
    on_poll: PollCallback | None = None,
    on_stdout_line: LineCallback | None = None,
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

    if process.stdout is None or process.stderr is None:
        _terminate(process)
        raise MediaProcessingError("Media tool pipes could not be created.")
    stdout_lines = _BoundedCapture()
    stderr_lines = _BoundedCapture()
    stdout_queue: Queue[str] = Queue()
    readers = (
        Thread(
            target=_read_lines,
            args=(process.stdout, stdout_lines, stdout_queue),
            daemon=True,
        ),
        Thread(
            target=_read_lines,
            args=(process.stderr, stderr_lines, None),
            daemon=True,
        ),
    )
    for reader in readers:
        reader.start()

    try:
        deadline = monotonic() + timeout
        while True:
            _drain_lines(stdout_queue, on_stdout_line)
            remaining = deadline - monotonic()
            if remaining <= 0:
                _terminate(process)
                raise MediaProcessTimeoutError("Media tool timed out.")
            try:
                process.wait(timeout=min(0.25, remaining))
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
    finally:
        for reader in readers:
            reader.join(timeout=2)

    _drain_lines(stdout_queue, on_stdout_line)
    return ProcessResult(
        returncode=process.returncode,
        stdout=stdout_lines.render(),
        stderr=stderr_lines.render(),
    )


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=2)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        process.kill()
        process.wait()


def _read_lines(
    stream: TextIO,
    captured: _BoundedCapture,
    output_queue: Queue[str] | None,
) -> None:
    try:
        while line := stream.readline(_MAX_LINE_CHARS):
            captured.append(line)
            if output_queue is not None:
                output_queue.put(line.rstrip("\r\n"))
    finally:
        stream.close()


def _drain_lines(output_queue: Queue[str], callback: LineCallback | None) -> None:
    while True:
        try:
            line = output_queue.get_nowait()
        except Empty:
            return
        if callback is not None:
            callback(line)


def safe_process_error(stderr: str, *, prefix: str = "FFmpeg failed") -> str:
    """Return a short user-safe summary from process stderr."""

    last_line = next(
        (line.strip() for line in reversed(stderr.splitlines()) if line.strip()),
        "unknown media processing error",
    )
    return f"{prefix}: {last_line[:500]}"
