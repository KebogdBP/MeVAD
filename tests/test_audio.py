import pytest

from mevad.audio import build_audio_format_selector
from mevad.models import AudioCodec


@pytest.mark.parametrize(
    ("codec", "expected"),
    [
        (AudioCodec.MP3, "bestaudio/best"),
        (AudioCodec.WAV, "bestaudio/best"),
        (AudioCodec.M4A, "bestaudio[ext=m4a]/bestaudio/best"),
        (AudioCodec.OPUS, "bestaudio[acodec^=opus]/bestaudio/best"),
    ],
)
def test_builds_trusted_audio_format_selector(codec: AudioCodec, expected: str) -> None:
    assert build_audio_format_selector(codec) == expected
