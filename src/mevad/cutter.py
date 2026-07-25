"""Video cutting boundary."""

from typing import Protocol

from mevad.downloader import CancellationToken, ProgressCallback
from mevad.models import VideoCutRequest, VideoCutResult


class VideoCutter(Protocol):
    """Port implemented by local media processing adapters."""

    def cut(
        self,
        request: VideoCutRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> VideoCutResult:
        """Create a clip from a local video."""
        ...
