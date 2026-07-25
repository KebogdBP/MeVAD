from collections.abc import Sequence
from pathlib import Path

import pytest

from mevad.adapters.process import LineCallback, PollCallback, ProcessResult
from mevad.adapters.yt_dlp_command import (
    YtDlpCommandAudioExtractor,
    YtDlpCommandVideoDownloader,
)
from mevad.downloader import CancellationToken
from mevad.exceptions import MediaDownloadError, UnsupportedMediaError
from mevad.models import (
    AudioBitrate,
    AudioCodec,
    AudioExtractionRequest,
    DownloadProgress,
    DownloadStatus,
    MediaSource,
    SourceKind,
    VideoContainer,
    VideoDownloadRequest,
    VideoQuality,
)


class FakeRunner:
    def __init__(
        self,
        output_path: Path,
        *,
        returncode: int = 0,
        metadata: bool = True,
        progress_lines: tuple[str, ...] = (),
    ) -> None:
        self.output_path = output_path
        self.returncode = returncode
        self.metadata = metadata
        self.progress_lines = progress_lines
        self.calls: list[tuple[list[str], float, CancellationToken | None]] = []

    def __call__(
        self,
        arguments: Sequence[str],
        *,
        timeout: float,
        cancellation: CancellationToken | None = None,
        on_poll: PollCallback | None = None,
        on_stdout_line: LineCallback | None = None,
    ) -> ProcessResult:
        self.calls.append((list(arguments), timeout, cancellation))
        if on_stdout_line is not None:
            for line in self.progress_lines:
                on_stdout_line(line)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_bytes(b"media")
        stdout = ""
        if self.metadata:
            stdout = f"MEVAD_ID=video-1\nMEVAD_TITLE=Example title\nMEVAD_PATH={self.output_path}\n"
        return ProcessResult(
            returncode=self.returncode,
            stdout=stdout,
            stderr="private upstream details",
        )


def test_managed_video_command_uses_typed_arguments(tmp_path: Path) -> None:
    output_path = tmp_path / "downloads" / "video.mp4"
    runner = FakeRunner(output_path)
    downloader = YtDlpCommandVideoDownloader(
        runner=runner,
        timeout_seconds=90,
        executable=("python", "-m", "yt_dlp"),
    )
    events: list[DownloadProgress] = []

    result = downloader.download(
        VideoDownloadRequest(
            source=_source(),
            output_directory=tmp_path / "downloads",
            quality=VideoQuality.P720,
            container=VideoContainer.MP4,
        ),
        on_progress=events.append,
    )

    arguments, timeout, _ = runner.calls[0]
    assert arguments[:3] == ["python", "-m", "yt_dlp"]
    assert arguments[arguments.index("--format") + 1]
    assert arguments[arguments.index("--merge-output-format") + 1] == "mp4"
    assert arguments[-1] == "https://example.com/video"
    assert timeout == 90
    assert result.output_path == output_path
    assert result.media_id == "video-1"
    assert [event.status for event in events] == [
        DownloadStatus.DOWNLOADING,
        DownloadStatus.COMPLETED,
    ]


def test_managed_audio_command_uses_codec_and_bitrate(tmp_path: Path) -> None:
    output_path = tmp_path / "audio" / "track.opus"
    runner = FakeRunner(output_path)
    extractor = YtDlpCommandAudioExtractor(
        runner=runner,
        executable=("yt-dlp",),
    )

    result = extractor.extract(
        AudioExtractionRequest(
            source=_source(),
            output_directory=tmp_path / "audio",
            codec=AudioCodec.OPUS,
            bitrate=AudioBitrate.K256,
        )
    )

    arguments = runner.calls[0][0]
    assert arguments[arguments.index("--audio-format") + 1] == "opus"
    assert arguments[arguments.index("--audio-quality") + 1] == "256K"
    assert result.codec is AudioCodec.OPUS
    assert result.output_path == output_path


def test_managed_command_normalizes_streaming_progress(tmp_path: Path) -> None:
    runner = FakeRunner(
        tmp_path / "video.mp4",
        progress_lines=(
            "ignored extractor output",
            "MEVAD_PROGRESS=25|100|NA|12.5|6",
            "MEVAD_PROGRESS=50|NA|200|NA|unknown",
            "MEVAD_PROGRESS=malformed",
            "MEVAD_PROCESSING=1",
        ),
    )
    downloader = YtDlpCommandVideoDownloader(runner=runner)
    events: list[DownloadProgress] = []

    downloader.download(
        VideoDownloadRequest(source=_source(), output_directory=tmp_path),
        on_progress=events.append,
    )

    assert [event.status for event in events] == [
        DownloadStatus.DOWNLOADING,
        DownloadStatus.DOWNLOADING,
        DownloadStatus.DOWNLOADING,
        DownloadStatus.PROCESSING,
        DownloadStatus.COMPLETED,
    ]
    first_progress = events[1]
    assert first_progress.downloaded_bytes == 25
    assert first_progress.total_bytes == 100
    assert first_progress.speed_bytes_per_second == 12.5
    assert first_progress.eta_seconds == 6
    estimated_progress = events[2]
    assert estimated_progress.total_bytes == 200
    assert estimated_progress.speed_bytes_per_second is None


def test_managed_wav_command_omits_bitrate(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path / "audio" / "track.wav")
    extractor = YtDlpCommandAudioExtractor(runner=runner, executable=("yt-dlp",))

    extractor.extract(
        AudioExtractionRequest(
            source=_source(),
            output_directory=tmp_path / "audio",
            codec=AudioCodec.WAV,
        )
    )

    assert "--audio-quality" not in runner.calls[0][0]
    assert "--progress-template" in runner.calls[0][0]


def test_managed_command_hides_stderr_on_failure(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path / "video.mp4", returncode=1)
    downloader = YtDlpCommandVideoDownloader(runner=runner)

    with pytest.raises(MediaDownloadError, match="command failed") as captured:
        downloader.download(
            VideoDownloadRequest(
                source=_source(),
                output_directory=tmp_path,
            )
        )

    assert "private upstream" not in str(captured.value)


def test_managed_command_rejects_incomplete_or_escaped_result(tmp_path: Path) -> None:
    missing = YtDlpCommandVideoDownloader(
        runner=FakeRunner(tmp_path / "missing.mp4", metadata=False)
    )
    with pytest.raises(MediaDownloadError, match="incomplete"):
        missing.download(VideoDownloadRequest(source=_source(), output_directory=tmp_path))

    escaped = YtDlpCommandVideoDownloader(runner=FakeRunner(tmp_path.parent / "escaped.mp4"))
    with pytest.raises(MediaDownloadError, match="invalid output path"):
        escaped.download(VideoDownloadRequest(source=_source(), output_directory=tmp_path))


def test_managed_command_rejects_local_source(tmp_path: Path) -> None:
    downloader = YtDlpCommandVideoDownloader(runner=FakeRunner(tmp_path / "video.mp4"))

    with pytest.raises(UnsupportedMediaError):
        downloader.download(
            VideoDownloadRequest(
                source=MediaSource(kind=SourceKind.LOCAL_FILE, value="video.mp4"),
                output_directory=tmp_path,
            )
        )


def _source() -> MediaSource:
    return MediaSource(
        kind=SourceKind.REMOTE_URL,
        value="https://EXAMPLE.com/video#fragment",
    )
