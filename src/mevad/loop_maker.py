"""GIF and loop rendering boundary."""

from typing import Protocol

from mevad.downloader import CancellationToken, ProgressCallback
from mevad.models import LoopRenderRequest, LoopRenderResult


class LoopMaker(Protocol):
    """Port implemented by local animation rendering adapters."""

    def render(
        self,
        request: LoopRenderRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> LoopRenderResult:
        """Render an animated image or loop-ready video."""
        ...
