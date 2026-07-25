import sys
from threading import Event, Thread
from time import sleep

import pytest

from mevad.adapters.process import run_process
from mevad.exceptions import DownloadCancelledError, MediaProcessTimeoutError


class EventToken:
    def __init__(self) -> None:
        self.event = Event()

    @property
    def is_cancelled(self) -> bool:
        return self.event.is_set()


def test_managed_process_captures_output() -> None:
    result = run_process(
        [sys.executable, "-c", "print('ready')"],
        timeout=5,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "ready"
    assert result.stderr == ""


def test_managed_process_enforces_hard_timeout() -> None:
    with pytest.raises(MediaProcessTimeoutError, match="timed out"):
        run_process(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=0.1,
        )


def test_managed_process_terminates_after_cancellation() -> None:
    token = EventToken()

    def cancel() -> None:
        sleep(0.1)
        token.event.set()

    thread = Thread(target=cancel)
    thread.start()
    try:
        with pytest.raises(DownloadCancelledError, match="cancelled"):
            run_process(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout=5,
                cancellation=token,
            )
    finally:
        thread.join()


def test_managed_process_invokes_poll_callback() -> None:
    polls: list[None] = []

    run_process(
        [sys.executable, "-c", "import time; time.sleep(0.35)"],
        timeout=5,
        on_poll=lambda: polls.append(None),
    )

    assert polls


def test_managed_process_streams_stdout_lines_in_order() -> None:
    lines: list[str] = []

    result = run_process(
        [
            sys.executable,
            "-c",
            "import time; print('first', flush=True); time.sleep(.3); print('second', flush=True)",
        ],
        timeout=5,
        on_stdout_line=lines.append,
    )

    assert lines == ["first", "second"]
    assert result.stdout.splitlines() == lines


def test_managed_process_bounds_captured_output() -> None:
    result = run_process(
        [sys.executable, "-c", "print('x' * 1_100_000)"],
        timeout=5,
    )

    assert len(result.stdout) <= 1_000_000


def test_managed_process_terminates_when_line_callback_fails() -> None:
    def fail_line(_line: str) -> None:
        raise RuntimeError("progress failed")

    with pytest.raises(RuntimeError, match="progress failed"):
        run_process(
            [
                sys.executable,
                "-c",
                "import time; print('progress', flush=True); time.sleep(10)",
            ],
            timeout=5,
            on_stdout_line=fail_line,
        )


def test_managed_process_terminates_when_poll_callback_fails() -> None:
    def fail_poll() -> None:
        raise RuntimeError("heartbeat failed")

    with pytest.raises(RuntimeError, match="heartbeat failed"):
        run_process(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=5,
            on_poll=fail_poll,
        )


def test_managed_process_honors_pre_cancelled_token() -> None:
    token = EventToken()
    token.event.set()

    with pytest.raises(DownloadCancelledError):
        run_process(
            [sys.executable, "-c", "print('must not run')"],
            timeout=5,
            cancellation=token,
        )


def test_managed_process_rejects_invalid_invocation() -> None:
    with pytest.raises(ValueError, match="positive"):
        run_process([sys.executable], timeout=0)
    with pytest.raises(ValueError, match="empty"):
        run_process([], timeout=1)
