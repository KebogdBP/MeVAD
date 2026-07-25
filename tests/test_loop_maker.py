from collections.abc import Sequence
from pathlib import Path

import pytest

from mevad.adapters.ffmpeg_loop import FFmpegLoopMaker
from mevad.adapters.process import PollCallback, ProcessResult
from mevad.downloader import CancellationToken
from mevad.exceptions import DownloadCancelledError, InvalidClipIntervalError, MediaProcessingError
from mevad.models import (
    ClipInterval,
    DownloadProgress,
    DownloadStatus,
    LoopFormat,
    LoopQuality,
    LoopRenderRequest,
    PlaybackSpeed,
)


class FakeRunner:
    def __init__(
        self,
        *,
        duration: str = "100",
        ffmpeg_returncode: int = 0,
        create_output: bool = True,
    ) -> None:
        self.duration = duration
        self.ffmpeg_returncode = ffmpeg_returncode
        self.create_output = create_output
        self.calls: list[tuple[list[str], float]] = []

    def __call__(
        self,
        arguments: Sequence[str],
        *,
        timeout: float,
        cancellation: CancellationToken | None = None,
        on_poll: PollCallback | None = None,
    ) -> ProcessResult:
        copied_arguments = list(arguments)
        self.calls.append((copied_arguments, timeout))
        if copied_arguments[0] == "ffprobe":
            return ProcessResult(returncode=0, stdout=self.duration, stderr="")
        if self.create_output:
            Path(copied_arguments[-1]).write_bytes(b"loop-data")
        return ProcessResult(
            returncode=self.ffmpeg_returncode,
            stdout="",
            stderr="render failed\n" if self.ffmpeg_returncode else "",
        )


class Token:
    def __init__(self, is_cancelled: bool = False) -> None:
        self.is_cancelled = is_cancelled


@pytest.mark.parametrize(
    ("width", "fps", "duration", "output_format"),
    [
        (159, 15, 1, LoopFormat.GIF),
        (640, 61, 1, LoopFormat.MP4),
        (640, 15, 31, LoopFormat.GIF),
        (1281, 15, 1, LoopFormat.WEBP),
        (640, 15, 121, LoopFormat.MP4),
    ],
)
def test_rejects_unsafe_render_limits(
    width: int,
    fps: int,
    duration: float,
    output_format: LoopFormat,
) -> None:
    with pytest.raises(MediaProcessingError):
        LoopRenderRequest(
            input_path=Path("input.mp4"),
            output_directory=Path("output"),
            interval=ClipInterval(0, duration),
            width=width,
            fps=fps,
            output_format=output_format,
        )


def test_output_duration_accounts_for_speed() -> None:
    request = LoopRenderRequest(
        input_path=Path("input.mp4"),
        output_directory=Path("output"),
        interval=ClipInterval(1, 5),
        speed=PlaybackSpeed.DOUBLE,
    )

    assert request.output_duration_seconds == 2.0


def test_renders_gif_with_palette_and_repeat(tmp_path: Path) -> None:
    runner = FakeRunner()
    maker = _maker(runner)
    events: list[DownloadProgress] = []

    result = maker.render(
        _request(
            tmp_path,
            output_format=LoopFormat.GIF,
            quality=LoopQuality.HIGH,
            speed=PlaybackSpeed.X1_5,
        ),
        on_progress=events.append,
    )

    assert result.output_path.suffix == ".gif"
    assert result.output_path.read_bytes() == b"loop-data"
    assert result.output_format is LoopFormat.GIF
    arguments = runner.calls[1][0]
    filter_graph = arguments[arguments.index("-filter_complex") + 1]
    assert "setpts=PTS/1.5,fps=15,scale=640:-2:flags=lanczos" in filter_graph
    assert "palettegen=max_colors=256" in filter_graph
    assert arguments[arguments.index("-loop") + 1] == "0"
    assert [event.status for event in events] == [
        DownloadStatus.PROCESSING,
        DownloadStatus.COMPLETED,
    ]


@pytest.mark.parametrize(
    ("output_format", "codec", "quality_option", "quality_value"),
    [
        (LoopFormat.WEBP, "libwebp_anim", "-quality", "50"),
        (LoopFormat.MP4, "libx264", "-crf", "28"),
        (LoopFormat.WEBM, "libvpx-vp9", "-crf", "40"),
    ],
)
def test_renders_video_and_webp_presets(
    tmp_path: Path,
    output_format: LoopFormat,
    codec: str,
    quality_option: str,
    quality_value: str,
) -> None:
    runner = FakeRunner()
    maker = _maker(runner)

    result = maker.render(
        _request(
            tmp_path,
            output_format=output_format,
            quality=LoopQuality.SMALL,
            repeat=False,
        )
    )

    arguments = runner.calls[1][0]
    assert result.output_path.suffix == f".{output_format.value}"
    assert codec in arguments
    assert arguments[arguments.index(quality_option) + 1] == quality_value
    assert "-an" in arguments


def test_rejects_interval_beyond_media_duration(tmp_path: Path) -> None:
    runner = FakeRunner(duration="2")
    maker = _maker(runner)

    with pytest.raises(InvalidClipIntervalError, match="exceeds media duration"):
        maker.render(
            LoopRenderRequest(
                input_path=_input_file(tmp_path),
                output_directory=tmp_path / "loops",
                interval=ClipInterval(1, 3),
            )
        )

    assert len(runner.calls) == 1


def test_removes_partial_output_after_ffmpeg_error(tmp_path: Path) -> None:
    runner = FakeRunner(ffmpeg_returncode=1)
    maker = _maker(runner)

    with pytest.raises(MediaProcessingError, match="render failed"):
        maker.render(_request(tmp_path))

    assert not list((tmp_path / "loops").glob("*.part.*"))


def test_rejects_missing_input(tmp_path: Path) -> None:
    maker = _maker(FakeRunner())

    with pytest.raises(MediaProcessingError, match="not found"):
        maker.render(
            LoopRenderRequest(
                input_path=tmp_path / "missing.mp4",
                output_directory=tmp_path,
                interval=ClipInterval(0, 1),
            )
        )


def test_honors_pre_cancelled_token(tmp_path: Path) -> None:
    maker = _maker(FakeRunner())

    with pytest.raises(DownloadCancelledError):
        maker.render(_request(tmp_path), cancellation=Token(is_cancelled=True))


def _maker(runner: FakeRunner) -> FFmpegLoopMaker:
    return FFmpegLoopMaker(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=runner,
    )


def _request(
    directory: Path,
    *,
    output_format: LoopFormat = LoopFormat.GIF,
    quality: LoopQuality = LoopQuality.BALANCED,
    speed: PlaybackSpeed = PlaybackSpeed.NORMAL,
    repeat: bool = True,
) -> LoopRenderRequest:
    return LoopRenderRequest(
        input_path=_input_file(directory),
        output_directory=directory / "loops",
        interval=ClipInterval(0, 2),
        output_format=output_format,
        quality=quality,
        speed=speed,
        repeat=repeat,
    )


def _input_file(directory: Path) -> Path:
    path = directory / "input.mp4"
    path.write_bytes(b"input-video")
    return path
