"""Shared safe subprocess boundary for local media tools."""

import os
import signal
import subprocess
import sys
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
    MediaResourceLimitError,
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


@dataclass(frozen=True, slots=True)
class ProcessLimits:
    """POSIX limits inherited by a media process and its descendants."""

    cpu_seconds: int = 7200
    memory_bytes: int = 2 * 1024 * 1024 * 1024
    file_size_bytes: int = 10 * 1024 * 1024 * 1024
    open_files: int = 256

    def __post_init__(self) -> None:
        if not 1 <= self.cpu_seconds <= 86400:
            raise ValueError("CPU limit must be between 1 and 86400 seconds.")
        if not 64 * 1024 * 1024 <= self.memory_bytes <= 128 * 1024 * 1024 * 1024:
            raise ValueError("Memory limit must be between 64 MiB and 128 GiB.")
        if not 1024 * 1024 <= self.file_size_bytes <= 1024**5:
            raise ValueError("File size limit must be between 1 MiB and 1 PiB.")
        if not 32 <= self.open_files <= 65536:
            raise ValueError("Open-files limit must be between 32 and 65536.")


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
    limits: ProcessLimits | None = None,
) -> ProcessResult:
    """Run a managed no-shell process with cancellation and hard timeout."""

    if timeout <= 0:
        raise ValueError("Process timeout must be positive.")
    if not arguments:
        raise ValueError("Process arguments cannot be empty.")
    if cancellation is not None and cancellation.is_cancelled:
        raise DownloadCancelledError("Media operation was cancelled.")
    try:
        process = _spawn_process(arguments, limits)
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
    if process.returncode in {
        -getattr(signal, "SIGXCPU", 24),
        -getattr(signal, "SIGXFSZ", 25),
    }:
        raise MediaResourceLimitError("Media process exceeded an OS resource limit.")
    return ProcessResult(
        returncode=process.returncode,
        stdout=stdout_lines.render(),
        stderr=stderr_lines.render(),
    )


def limited_process_runner(limits: ProcessLimits) -> ProcessRunner:
    """Bind one validated limits policy to the shared runner."""

    def runner(
        arguments: Sequence[str],
        *,
        timeout: float,
        cancellation: CancellationToken | None = None,
        on_poll: PollCallback | None = None,
        on_stdout_line: LineCallback | None = None,
    ) -> ProcessResult:
        return run_process(
            arguments,
            timeout=timeout,
            cancellation=cancellation,
            on_poll=on_poll,
            on_stdout_line=on_stdout_line,
            limits=limits,
        )

    return runner


def _spawn_process(
    arguments: Sequence[str],
    limits: ProcessLimits | None,
) -> subprocess.Popen[str]:
    preexec = _resource_preexec(limits)
    if preexec is None:
        return subprocess.Popen(
            list(arguments),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            start_new_session=True,
        )
    return subprocess.Popen(
        list(arguments),
        preexec_fn=preexec,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        start_new_session=True,
    )


def _resource_preexec(limits: ProcessLimits | None) -> Callable[[], None] | None:
    if limits is None or not sys.platform.startswith("linux"):
        return None
    import resource

    def apply() -> None:
        for resource_name, requested in (
            (resource.RLIMIT_CPU, limits.cpu_seconds),
            (resource.RLIMIT_AS, limits.memory_bytes),
            (resource.RLIMIT_FSIZE, limits.file_size_bytes),
            (resource.RLIMIT_NOFILE, limits.open_files),
        ):
            _, hard = resource.getrlimit(resource_name)
            selected = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
            resource.setrlimit(resource_name, (selected, selected))

    return apply


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
