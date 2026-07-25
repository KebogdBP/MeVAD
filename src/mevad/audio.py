"""Audio extraction boundary and trusted yt-dlp format planning."""

from typing import Protocol

from mevad.downloader import CancellationToken, ProgressCallback
from mevad.models import (
    AudioCodec,
    AudioExtractionRequest,
    AudioExtractionResult,
)


class AudioExtractor(Protocol):
    """Port implemented by remote-media audio extraction adapters."""

    def extract(
        self,
        request: AudioExtractionRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> AudioExtractionResult:
        """Download the best audio stream and convert it to the requested codec."""
        ...


def build_audio_format_selector(codec: AudioCodec) -> str:
    """Prefer a source stream compatible with the requested output codec."""

    if codec is AudioCodec.M4A:
        return "bestaudio[ext=m4a]/bestaudio/best"
    if codec is AudioCodec.OPUS:
        return "bestaudio[acodec^=opus]/bestaudio/best"
    return "bestaudio/best"
