"""Safe subprocess adapter for FFmpeg video cutting."""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mevad.cutter import VideoCutter
from mevad.downloader import CancellationToken, ProgressCallback
from mevad.exceptions import (
    DownloadCancelledError,
    InvalidClipIntervalError,
    MediaProcessingError,
    MissingRuntimeToolError,
)
from mevad.models import (
    CutMode,
    DownloadProgress,
    DownloadStatus,
    VideoCutRequest,
    VideoCutResult,
)
from mevad.runtime import discover_runtime_tools


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Captured external process result."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Injectable no-shell process runner."""

    def __call__(self, arguments: Sequence[str], *, timeout: float) -> ProcessResult:
        """Run one bounded external process."""
        ...


class FFmpegVideoCutter(VideoCutter):
    """Cut local video through argument-array FFprobe and FFmpeg calls."""

    def __init__(
        self,
        *,
        ffmpeg_path: str | None = None,
        ffprobe_path: str | None = None,
        runner: ProcessRunner | None = None,
        discover_tools: bool = True,
    ) -> None:
        tools = discover_runtime_tools() if discover_tools else None
        self._ffmpeg_path = ffmpeg_path or (tools.ffmpeg if tools else None)
        self._ffprobe_path = ffprobe_path or (tools.ffprobe if tools else None)
        self._runner = runner or _run_process

    def cut(
        self,
        request: VideoCutRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> VideoCutResult:
        _raise_if_cancelled(cancellation)
        ffmpeg_path, ffprobe_path = self._required_tools()
        input_path = request.input_path.expanduser().resolve()
        if not input_path.is_file():
            raise MediaProcessingError("Input video file was not found.")

        media_duration = self._probe_duration(ffprobe_path, input_path)
        if request.interval.end_seconds > media_duration + 0.001:
            raise InvalidClipIntervalError(
                f"Clip end exceeds media duration ({_format_seconds(media_duration)} seconds)."
            )

        output_directory = request.output_directory.expanduser().resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        output_path = _build_output_path(request, input_path, output_directory)
        if output_path.exists():
            raise MediaProcessingError("Output clip already exists.")
        temporary_path = output_path.with_name(f"{output_path.stem}.part{output_path.suffix}")
        if temporary_path.exists():
            raise MediaProcessingError("Temporary output clip already exists.")

        _raise_if_cancelled(cancellation)
        if on_progress is not None:
            on_progress(DownloadProgress(status=DownloadStatus.PROCESSING))

        arguments = _build_ffmpeg_arguments(
            ffmpeg_path=ffmpeg_path,
            input_path=input_path,
            output_path=temporary_path,
            request=request,
        )
        timeout = _processing_timeout(request)
        try:
            result = self._runner(arguments, timeout=timeout)
        except MediaProcessingError:
            temporary_path.unlink(missing_ok=True)
            raise
        if result.returncode != 0:
            temporary_path.unlink(missing_ok=True)
            raise MediaProcessingError(_safe_process_error(result.stderr))

        if cancellation is not None and cancellation.is_cancelled:
            temporary_path.unlink(missing_ok=True)
            raise DownloadCancelledError("Video cutting was cancelled.")
        if not temporary_path.is_file():
            raise MediaProcessingError("FFmpeg completed without creating an output file.")
        temporary_path.replace(output_path)

        cut_result = VideoCutResult(
            output_path=output_path,
            duration_seconds=request.interval.duration_seconds,
            filesize_bytes=output_path.stat().st_size,
            mode=request.mode,
        )
        if on_progress is not None:
            on_progress(
                DownloadProgress(
                    status=DownloadStatus.COMPLETED,
                    downloaded_bytes=cut_result.filesize_bytes,
                    total_bytes=cut_result.filesize_bytes,
                    filename=str(cut_result.output_path),
                )
            )
        return cut_result

    def _required_tools(self) -> tuple[str, str]:
        if self._ffmpeg_path is None:
            raise MissingRuntimeToolError("FFmpeg was not found.")
        if self._ffprobe_path is None:
            raise MissingRuntimeToolError("FFprobe was not found.")
        return self._ffmpeg_path, self._ffprobe_path

    def _probe_duration(self, ffprobe_path: str, input_path: Path) -> float:
        result = self._runner(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(input_path),
            ],
            timeout=30,
        )
        if result.returncode != 0:
            raise MediaProcessingError(_safe_process_error(result.stderr, prefix="FFprobe failed"))
        try:
            duration = float(result.stdout.strip())
        except ValueError as error:
            raise MediaProcessingError("FFprobe returned an invalid media duration.") from error
        if duration <= 0:
            raise MediaProcessingError("Input media duration must be positive.")
        return duration


def _build_ffmpeg_arguments(
    *,
    ffmpeg_path: str,
    input_path: Path,
    output_path: Path,
    request: VideoCutRequest,
) -> list[str]:
    interval = request.interval
    common = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-n",
        "-ss",
        _format_seconds(interval.start_seconds),
        "-i",
        str(input_path),
        "-t",
        _format_seconds(interval.duration_seconds),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]
    if request.mode is CutMode.FAST:
        codec_arguments = ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    else:
        codec_arguments = [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
        ]
    return [*common, *codec_arguments, str(output_path)]


def _build_output_path(
    request: VideoCutRequest,
    input_path: Path,
    output_directory: Path,
) -> Path:
    start = _filename_timestamp(request.interval.start_seconds)
    end = _filename_timestamp(request.interval.end_seconds)
    suffix = input_path.suffix.lower() if request.mode is CutMode.FAST else ".mp4"
    if not suffix:
        suffix = ".mkv" if request.mode is CutMode.FAST else ".mp4"
    stem = input_path.stem[:140]
    return output_directory / f"{stem}.clip-{start}-{end}{suffix}"


def _processing_timeout(request: VideoCutRequest) -> float:
    duration = request.interval.duration_seconds
    if request.mode is CutMode.FAST:
        return max(60.0, min(duration + 30.0, 600.0))
    return max(120.0, min(duration * 4.0 + 60.0, 7200.0))


def _run_process(arguments: Sequence[str], *, timeout: float) -> ProcessResult:
    try:
        completed = subprocess.run(
            list(arguments),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        raise MediaProcessingError("Media tool timed out.") from error
    except OSError as error:
        raise MediaProcessingError(f"Media tool could not start: {error}") from error
    return ProcessResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _raise_if_cancelled(cancellation: CancellationToken | None) -> None:
    if cancellation is not None and cancellation.is_cancelled:
        raise DownloadCancelledError("Video cutting was cancelled.")


def _safe_process_error(stderr: str, *, prefix: str = "FFmpeg failed") -> str:
    last_line = next(
        (line.strip() for line in reversed(stderr.splitlines()) if line.strip()),
        "unknown media processing error",
    )
    return f"{prefix}: {last_line[:500]}"


def _format_seconds(value: float) -> str:
    return f"{value:.3f}"


def _filename_timestamp(value: float) -> str:
    return f"{value:.3f}".replace(".", "_")
