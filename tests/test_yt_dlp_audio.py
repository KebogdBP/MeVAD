from collections.abc import Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

from mevad.adapters.yt_dlp_audio import AudioClient, YtDlpAudioExtractor
from mevad.exceptions import DownloadCancelledError, MediaDownloadError, UnsupportedMediaError
from mevad.models import (
    AudioBitrate,
    AudioCodec,
    AudioExtractionRequest,
    DownloadProgress,
    DownloadStatus,
    MediaSource,
    SourceKind,
)


class FakeAudioClient(AbstractContextManager[AudioClient]):
    def __init__(
        self,
        options: Mapping[str, Any],
        output_path: Path,
        *,
        error: Exception | None = None,
    ) -> None:
        self.options = options
        self.output_path = output_path
        self.error = error
        self.requested_url: str | None = None
        self.download: bool | None = None

    def __enter__(self) -> AudioClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def extract_info(self, url: str, *, download: bool) -> Mapping[str, Any] | None:
        if self.error is not None:
            raise self.error
        self.requested_url = url
        self.download = download
        self.output_path.write_bytes(b"audio-data")

        progress_hook = self.options["progress_hooks"][0]
        progress_hook(
            {
                "status": "downloading",
                "downloaded_bytes": 5,
                "total_bytes_estimate": 10,
                "speed": 3,
                "eta": 1,
                "filename": str(self.output_path.with_suffix(".part")),
            }
        )
        progress_hook(
            {
                "status": "finished",
                "downloaded_bytes": 10,
                "total_bytes": 10,
                "filename": str(self.output_path.with_suffix(".webm")),
            }
        )
        postprocessor_hook = self.options["postprocessor_hooks"][0]
        postprocessor_hook(
            {
                "status": "finished",
                "info_dict": {"filepath": str(self.output_path)},
            }
        )
        return {
            "id": "audio-1",
            "title": "Example audio",
            "filepath": str(self.output_path),
        }


class Token:
    def __init__(self, is_cancelled: bool = False) -> None:
        self.is_cancelled = is_cancelled


def test_extracts_mp3_and_emits_progress(tmp_path: Path) -> None:
    output_path = tmp_path / "Example [audio-1].mp3"
    captured_options: Mapping[str, Any] | None = None

    def factory(options: Mapping[str, Any]) -> FakeAudioClient:
        nonlocal captured_options
        captured_options = options
        return FakeAudioClient(options, output_path)

    events: list[DownloadProgress] = []
    extractor = YtDlpAudioExtractor(client_factory=factory)

    result = extractor.extract(
        AudioExtractionRequest(
            source=MediaSource(
                kind=SourceKind.REMOTE_URL,
                value="https://EXAMPLE.com/audio#fragment",
            ),
            output_directory=tmp_path,
            codec=AudioCodec.MP3,
            bitrate=AudioBitrate.K320,
        ),
        on_progress=events.append,
    )

    assert result.media_id == "audio-1"
    assert result.codec is AudioCodec.MP3
    assert result.output_path == output_path
    assert result.filesize_bytes == len(b"audio-data")
    assert [event.status for event in events] == [
        DownloadStatus.DOWNLOADING,
        DownloadStatus.PROCESSING,
        DownloadStatus.PROCESSING,
        DownloadStatus.COMPLETED,
    ]
    assert events[0].fraction == 0.5
    assert captured_options is not None
    assert captured_options["noplaylist"] is True
    assert captured_options["format"] == "bestaudio/best"
    assert captured_options["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }
    ]


def test_wav_omits_irrelevant_bitrate(tmp_path: Path) -> None:
    output_path = tmp_path / "audio.wav"
    captured_options: Mapping[str, Any] | None = None

    def factory(options: Mapping[str, Any]) -> FakeAudioClient:
        nonlocal captured_options
        captured_options = options
        return FakeAudioClient(options, output_path)

    extractor = YtDlpAudioExtractor(client_factory=factory)
    extractor.extract(
        AudioExtractionRequest(
            source=MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/audio"),
            output_directory=tmp_path,
            codec=AudioCodec.WAV,
        )
    )

    assert captured_options is not None
    assert captured_options["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        }
    ]


def test_rejects_path_outside_output_directory(tmp_path: Path) -> None:
    outside_path = tmp_path.parent / "outside.mp3"
    extractor = YtDlpAudioExtractor(
        client_factory=lambda options: FakeAudioClient(options, outside_path)
    )

    with pytest.raises(MediaDownloadError, match="outside the output directory"):
        extractor.extract(_request(tmp_path))


def test_rejects_local_file_source(tmp_path: Path) -> None:
    extractor = YtDlpAudioExtractor()
    request = AudioExtractionRequest(
        source=MediaSource(kind=SourceKind.LOCAL_FILE, value="/tmp/video.mp4"),
        output_directory=tmp_path,
    )

    with pytest.raises(UnsupportedMediaError, match="remote URLs only"):
        extractor.extract(request)


def test_honors_pre_cancelled_token(tmp_path: Path) -> None:
    extractor = YtDlpAudioExtractor()

    with pytest.raises(DownloadCancelledError):
        extractor.extract(_request(tmp_path), cancellation=Token(is_cancelled=True))


def test_converts_external_failure_to_domain_error(tmp_path: Path) -> None:
    output_path = tmp_path / "audio.mp3"
    extractor = YtDlpAudioExtractor(
        client_factory=lambda options: FakeAudioClient(
            options,
            output_path,
            error=RuntimeError("upstream failed"),
        )
    )

    with pytest.raises(MediaDownloadError, match="upstream failed"):
        extractor.extract(_request(tmp_path))


def _request(output_directory: Path) -> AudioExtractionRequest:
    return AudioExtractionRequest(
        source=MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/audio"),
        output_directory=output_directory,
    )
