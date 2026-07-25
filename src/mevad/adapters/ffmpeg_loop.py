"""Safe FFmpeg adapter for GIF, WebP, MP4, and WebM loops."""

from pathlib import Path

from mevad.adapters.process import ProcessRunner, run_process, safe_process_error
from mevad.downloader import CancellationToken, ProgressCallback
from mevad.exceptions import (
    DownloadCancelledError,
    InvalidClipIntervalError,
    MediaProcessingError,
    MissingRuntimeToolError,
)
from mevad.loop_maker import LoopMaker
from mevad.models import (
    DownloadProgress,
    DownloadStatus,
    LoopFormat,
    LoopQuality,
    LoopRenderRequest,
    LoopRenderResult,
)
from mevad.runtime import discover_runtime_tools


class FFmpegLoopMaker(LoopMaker):
    """Render bounded local animations through FFmpeg."""

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
        self._runner = runner or run_process

    def render(
        self,
        request: LoopRenderRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> LoopRenderResult:
        _raise_if_cancelled(cancellation)
        ffmpeg_path, ffprobe_path = self._required_tools()
        input_path = request.input_path.expanduser().resolve()
        if not input_path.is_file():
            raise MediaProcessingError("Input video file was not found.")

        media_duration = self._probe_duration(ffprobe_path, input_path)
        if request.interval.end_seconds > media_duration + 0.001:
            raise InvalidClipIntervalError(
                f"Loop end exceeds media duration ({_format_seconds(media_duration)} seconds)."
            )

        output_directory = request.output_directory.expanduser().resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        output_path = _build_output_path(request, input_path, output_directory)
        temporary_path = output_path.with_name(f"{output_path.stem}.part{output_path.suffix}")
        if output_path.exists():
            raise MediaProcessingError("Loop output already exists.")
        if temporary_path.exists():
            raise MediaProcessingError("Temporary loop output already exists.")

        _raise_if_cancelled(cancellation)
        if on_progress is not None:
            on_progress(DownloadProgress(status=DownloadStatus.PROCESSING))

        arguments = _build_ffmpeg_arguments(
            ffmpeg_path=ffmpeg_path,
            input_path=input_path,
            output_path=temporary_path,
            request=request,
        )
        try:
            process_result = self._runner(
                arguments,
                timeout=_processing_timeout(request),
            )
        except MediaProcessingError:
            temporary_path.unlink(missing_ok=True)
            raise
        if process_result.returncode != 0:
            temporary_path.unlink(missing_ok=True)
            raise MediaProcessingError(safe_process_error(process_result.stderr))
        if cancellation is not None and cancellation.is_cancelled:
            temporary_path.unlink(missing_ok=True)
            raise DownloadCancelledError("Loop rendering was cancelled.")
        if not temporary_path.is_file():
            raise MediaProcessingError("FFmpeg completed without creating a loop output.")

        temporary_path.replace(output_path)
        result = LoopRenderResult(
            output_path=output_path,
            output_format=request.output_format,
            duration_seconds=request.output_duration_seconds,
            width=request.width,
            fps=request.fps,
            filesize_bytes=output_path.stat().st_size,
        )
        if on_progress is not None:
            on_progress(
                DownloadProgress(
                    status=DownloadStatus.COMPLETED,
                    downloaded_bytes=result.filesize_bytes,
                    total_bytes=result.filesize_bytes,
                    filename=str(result.output_path),
                )
            )
        return result

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
            raise MediaProcessingError(safe_process_error(result.stderr, prefix="FFprobe failed"))
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
    request: LoopRenderRequest,
) -> list[str]:
    base = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-n",
        "-ss",
        _format_seconds(request.interval.start_seconds),
        "-i",
        str(input_path),
        "-t",
        _format_seconds(request.interval.duration_seconds),
        "-an",
    ]
    filter_graph = _base_filter(request)

    if request.output_format is LoopFormat.GIF:
        colors = {
            LoopQuality.SMALL: 64,
            LoopQuality.BALANCED: 128,
            LoopQuality.HIGH: 256,
        }[request.quality]
        gif_filter = (
            f"{filter_graph},split[palette_source][gif_source];"
            f"[palette_source]palettegen=max_colors={colors}:stats_mode=diff[palette];"
            "[gif_source][palette]paletteuse=dither=sierra2_4a"
        )
        codec_arguments = [
            "-filter_complex",
            gif_filter,
            "-loop",
            "0" if request.repeat else "-1",
        ]
    elif request.output_format is LoopFormat.WEBP:
        quality = {
            LoopQuality.SMALL: "50",
            LoopQuality.BALANCED: "75",
            LoopQuality.HIGH: "90",
        }[request.quality]
        codec_arguments = [
            "-vf",
            filter_graph,
            "-c:v",
            "libwebp_anim",
            "-quality",
            quality,
            "-loop",
            "0" if request.repeat else "1",
        ]
    elif request.output_format is LoopFormat.MP4:
        crf = {
            LoopQuality.SMALL: "28",
            LoopQuality.BALANCED: "23",
            LoopQuality.HIGH: "18",
        }[request.quality]
        codec_arguments = [
            "-vf",
            filter_graph,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            crf,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
        ]
    else:
        crf = {
            LoopQuality.SMALL: "40",
            LoopQuality.BALANCED: "32",
            LoopQuality.HIGH: "24",
        }[request.quality]
        codec_arguments = [
            "-vf",
            filter_graph,
            "-c:v",
            "libvpx-vp9",
            "-crf",
            crf,
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
        ]
    return [*base, *codec_arguments, str(output_path)]


def _base_filter(request: LoopRenderRequest) -> str:
    return (
        f"setpts=PTS/{request.speed.value},fps={request.fps},scale={request.width}:-2:flags=lanczos"
    )


def _build_output_path(
    request: LoopRenderRequest,
    input_path: Path,
    output_directory: Path,
) -> Path:
    start = _filename_timestamp(request.interval.start_seconds)
    end = _filename_timestamp(request.interval.end_seconds)
    stem = input_path.stem[:130]
    return output_directory / (
        f"{stem}.loop-{start}-{end}-{request.width}w-{request.fps}fps.{request.output_format.value}"
    )


def _processing_timeout(request: LoopRenderRequest) -> float:
    complexity = request.output_duration_seconds * request.width * request.fps / 100_000
    return max(120.0, min(120.0 + complexity * 20.0, 3600.0))


def _raise_if_cancelled(cancellation: CancellationToken | None) -> None:
    if cancellation is not None and cancellation.is_cancelled:
        raise DownloadCancelledError("Loop rendering was cancelled.")


def _format_seconds(value: float) -> str:
    return f"{value:.3f}"


def _filename_timestamp(value: float) -> str:
    return f"{value:.3f}".replace(".", "_")
