from collections.abc import Sequence
from pathlib import Path

import pytest

from mevad.adapters.ffmpeg_cutter import FFmpegVideoCutter
from mevad.adapters.process import ProcessResult
from mevad.exceptions import (
    DownloadCancelledError,
    InvalidClipIntervalError,
    MediaProcessingError,
    MissingRuntimeToolError,
)
from mevad.models import (
    ClipInterval,
    CutMode,
    DownloadProgress,
    DownloadStatus,
    VideoCutRequest,
)


class FakeRunner:
    def __init__(
        self,
        *,
        duration: str = "100.0",
        ffmpeg_returncode: int = 0,
        create_output: bool = True,
    ) -> None:
        self.duration = duration
        self.ffmpeg_returncode = ffmpeg_returncode
        self.create_output = create_output
        self.calls: list[tuple[list[str], float]] = []

    def __call__(self, arguments: Sequence[str], *, timeout: float) -> ProcessResult:
        self.calls.append((list(arguments), timeout))
        if arguments[0] == "ffprobe":
            return ProcessResult(returncode=0, stdout=self.duration, stderr="")
        if self.create_output:
            Path(arguments[-1]).write_bytes(b"clip-data")
        return ProcessResult(
            returncode=self.ffmpeg_returncode,
            stdout="",
            stderr="encoder failed\n" if self.ffmpeg_returncode else "",
        )


class Token:
    def __init__(self, is_cancelled: bool = False) -> None:
        self.is_cancelled = is_cancelled


def test_interval_validates_boundaries() -> None:
    interval = ClipInterval(start_seconds=1.25, end_seconds=3.75)

    assert interval.duration_seconds == 2.5


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (-1.0, 2.0),
        (2.0, 2.0),
        (3.0, 2.0),
        (float("nan"), 2.0),
        (0.0, float("inf")),
    ],
)
def test_interval_rejects_invalid_values(start: float, end: float) -> None:
    with pytest.raises(InvalidClipIntervalError):
        ClipInterval(start_seconds=start, end_seconds=end)


def test_accurate_cut_uses_reencode_and_atomic_output(tmp_path: Path) -> None:
    input_path = _input_file(tmp_path)
    runner = FakeRunner()
    cutter = FFmpegVideoCutter(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=runner,
    )
    events: list[DownloadProgress] = []

    result = cutter.cut(
        VideoCutRequest(
            input_path=input_path,
            output_directory=tmp_path / "clips",
            interval=ClipInterval(start_seconds=10.0, end_seconds=15.5),
            mode=CutMode.ACCURATE,
        ),
        on_progress=events.append,
    )

    assert result.output_path.name == "input.clip-10_000-15_500.mp4"
    assert result.output_path.read_bytes() == b"clip-data"
    assert result.duration_seconds == 5.5
    assert result.mode is CutMode.ACCURATE
    ffmpeg_arguments = runner.calls[1][0]
    assert ffmpeg_arguments[:6] == [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-n",
    ]
    assert ffmpeg_arguments[6:8] == ["-ss", "10.000"]
    assert "-c:v" in ffmpeg_arguments
    assert "libx264" in ffmpeg_arguments
    assert ffmpeg_arguments[-1].endswith(".part.mp4")
    assert [event.status for event in events] == [
        DownloadStatus.PROCESSING,
        DownloadStatus.COMPLETED,
    ]


def test_fast_cut_uses_stream_copy_and_preserves_extension(tmp_path: Path) -> None:
    input_path = _input_file(tmp_path, suffix=".mkv")
    runner = FakeRunner()
    cutter = FFmpegVideoCutter(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=runner,
    )

    result = cutter.cut(
        VideoCutRequest(
            input_path=input_path,
            output_directory=tmp_path / "clips",
            interval=ClipInterval(start_seconds=0, end_seconds=3),
            mode=CutMode.FAST,
        )
    )

    assert result.output_path.suffix == ".mkv"
    ffmpeg_arguments = runner.calls[1][0]
    assert ffmpeg_arguments[-5:-3] == ["-c", "copy"]
    assert runner.calls[1][1] == 60.0


def test_rejects_interval_beyond_media_duration(tmp_path: Path) -> None:
    input_path = _input_file(tmp_path)
    runner = FakeRunner(duration="10")
    cutter = FFmpegVideoCutter(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=runner,
    )

    with pytest.raises(InvalidClipIntervalError, match="exceeds media duration"):
        cutter.cut(
            VideoCutRequest(
                input_path=input_path,
                output_directory=tmp_path / "clips",
                interval=ClipInterval(start_seconds=5, end_seconds=11),
            )
        )

    assert len(runner.calls) == 1


def test_removes_partial_output_when_ffmpeg_fails(tmp_path: Path) -> None:
    input_path = _input_file(tmp_path)
    runner = FakeRunner(ffmpeg_returncode=1)
    cutter = FFmpegVideoCutter(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=runner,
    )

    with pytest.raises(MediaProcessingError, match="encoder failed"):
        cutter.cut(
            VideoCutRequest(
                input_path=input_path,
                output_directory=tmp_path / "clips",
                interval=ClipInterval(start_seconds=1, end_seconds=2),
            )
        )

    assert not list((tmp_path / "clips").glob("*.part.*"))


def test_rejects_missing_input(tmp_path: Path) -> None:
    cutter = FFmpegVideoCutter(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=FakeRunner(),
    )

    with pytest.raises(MediaProcessingError, match="not found"):
        cutter.cut(
            VideoCutRequest(
                input_path=tmp_path / "missing.mp4",
                output_directory=tmp_path,
                interval=ClipInterval(start_seconds=0, end_seconds=1),
            )
        )


def test_rejects_missing_runtime_tools(tmp_path: Path) -> None:
    input_path = _input_file(tmp_path)
    cutter = FFmpegVideoCutter(
        ffmpeg_path=None,
        ffprobe_path=None,
        runner=FakeRunner(),
        discover_tools=False,
    )

    with pytest.raises(MissingRuntimeToolError, match="FFmpeg"):
        cutter.cut(
            VideoCutRequest(
                input_path=input_path,
                output_directory=tmp_path,
                interval=ClipInterval(start_seconds=0, end_seconds=1),
            )
        )


def test_honors_pre_cancelled_token(tmp_path: Path) -> None:
    cutter = FFmpegVideoCutter(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=FakeRunner(),
    )

    with pytest.raises(DownloadCancelledError):
        cutter.cut(
            VideoCutRequest(
                input_path=tmp_path / "input.mp4",
                output_directory=tmp_path,
                interval=ClipInterval(start_seconds=0, end_seconds=1),
            ),
            cancellation=Token(is_cancelled=True),
        )


def _input_file(directory: Path, *, suffix: str = ".mp4") -> Path:
    path = directory / f"input{suffix}"
    path.write_bytes(b"input-video")
    return path
