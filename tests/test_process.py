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
