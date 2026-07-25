import pytest

from mevad_api.config import Settings
from mevad_worker.outbox_runtime import create_outbox_relay


def test_outbox_runtime_requires_durable_backends() -> None:
    with pytest.raises(RuntimeError, match="requires postgres and redis"):
        create_outbox_relay(
            Settings(
                job_backend="memory",
                queue_backend="memory",
                require_media_tools=False,
            )
        )
