"""Media analyzer boundary shared by CLI and future workers."""

from typing import Protocol

from mevad.models import MediaAnalysis, MediaSource


class MediaAnalyzer(Protocol):
    """Port implemented by metadata extraction adapters."""

    def analyze(self, source: MediaSource) -> MediaAnalysis:
        """Analyze a source without downloading its media payload."""
        ...
