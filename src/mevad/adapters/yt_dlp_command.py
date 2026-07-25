"""Managed yt-dlp command adapters for isolated worker execution."""

import sys
from collections.abc import Sequence
from pathlib import Path

from mevad.adapters.process import ProcessResult, ProcessRunner, run_process
from mevad.audio import AudioExtractor, build_audio_format_selector
from mevad.downloader import (
    CancellationToken,
    ProgressCallback,
    VideoDownloader,
    build_video_format_selector,
)
from mevad.exceptions import MediaDownloadError, UnsupportedMediaError
from mevad.models import (
    AudioCodec,
    AudioExtractionRequest,
    AudioExtractionResult,
    DownloadProgress,
    DownloadStatus,
    SourceKind,
    VideoContainer,
    VideoDownloadRequest,
    VideoDownloadResult,
)
from mevad.security import normalize_remote_url

_ID_MARKER = "MEVAD_ID="
_TITLE_MARKER = "MEVAD_TITLE="
_PATH_MARKER = "MEVAD_PATH="


class YtDlpCommandVideoDownloader(VideoDownloader):
    """Download video in a cancellable yt-dlp subprocess."""

    def __init__(
        self,
        *,
        runner: ProcessRunner = run_process,
        timeout_seconds: float = 7200,
        executable: Sequence[str] | None = None,
    ) -> None:
        self._runner = runner
        self._timeout = timeout_seconds
        self._executable = tuple(executable or (sys.executable, "-m", "yt_dlp"))

    def download(
        self,
        request: VideoDownloadRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> VideoDownloadResult:
        _require_remote(request.source.kind)
        output_directory = _prepare_output_directory(request.output_directory)
        _notify_started(on_progress)
        arguments = [
            *self._executable,
            *_common_arguments(output_directory),
            "--format",
            build_video_format_selector(request.quality, request.container),
        ]
        if request.container is not VideoContainer.AUTO:
            arguments.extend(["--merge-output-format", request.container.value])
        arguments.append(normalize_remote_url(request.source.value))
        result = self._runner(
            arguments,
            timeout=self._timeout,
            cancellation=cancellation,
        )
        media_id, title, output_path = _parse_result(result, output_directory)
        download = VideoDownloadResult(
            media_id=media_id,
            title=title,
            output_path=output_path,
            filesize_bytes=output_path.stat().st_size,
        )
        _notify_completed(on_progress, output_path, download.filesize_bytes)
        return download


class YtDlpCommandAudioExtractor(AudioExtractor):
    """Download and transcode audio in a cancellable yt-dlp subprocess."""

    def __init__(
        self,
        *,
        runner: ProcessRunner = run_process,
        timeout_seconds: float = 7200,
        executable: Sequence[str] | None = None,
    ) -> None:
        self._runner = runner
        self._timeout = timeout_seconds
        self._executable = tuple(executable or (sys.executable, "-m", "yt_dlp"))

    def extract(
        self,
        request: AudioExtractionRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> AudioExtractionResult:
        _require_remote(request.source.kind)
        output_directory = _prepare_output_directory(request.output_directory)
        _notify_started(on_progress)
        arguments = [
            *self._executable,
            *_common_arguments(output_directory),
            "--format",
            build_audio_format_selector(request.codec),
            "--extract-audio",
            "--audio-format",
            request.codec.value,
        ]
        if request.codec is not AudioCodec.WAV:
            arguments.extend(["--audio-quality", f"{request.bitrate.value}K"])
        arguments.append(normalize_remote_url(request.source.value))
        result = self._runner(
            arguments,
            timeout=self._timeout,
            cancellation=cancellation,
        )
        media_id, title, output_path = _parse_result(result, output_directory)
        extraction = AudioExtractionResult(
            media_id=media_id,
            title=title,
            codec=request.codec,
            output_path=output_path,
            filesize_bytes=output_path.stat().st_size,
        )
        _notify_completed(on_progress, output_path, extraction.filesize_bytes)
        return extraction


def _common_arguments(output_directory: Path) -> list[str]:
    return [
        "--no-playlist",
        "--no-warnings",
        "--no-overwrites",
        "--continue",
        "--newline",
        "--socket-timeout",
        "15",
        "--retries",
        "2",
        "--fragment-retries",
        "2",
        "--extractor-retries",
        "1",
        "--paths",
        str(output_directory),
        "--output",
        "%(title).180B [%(id)s].%(ext)s",
        "--windows-filenames",
        "--trim-filenames",
        "220",
        "--no-simulate",
        "--print",
        f"after_move:{_ID_MARKER}%(id)s",
        "--print",
        f"after_move:{_TITLE_MARKER}%(title)s",
        "--print",
        f"after_move:{_PATH_MARKER}%(filepath)s",
    ]


def _parse_result(result: ProcessResult, output_directory: Path) -> tuple[str, str, Path]:
    if result.returncode != 0:
        raise MediaDownloadError("yt-dlp command failed.")
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        for marker, key in (
            (_ID_MARKER, "id"),
            (_TITLE_MARKER, "title"),
            (_PATH_MARKER, "path"),
        ):
            if line.startswith(marker):
                values[key] = line.removeprefix(marker).strip()
    if not values.get("id") or not values.get("title") or not values.get("path"):
        raise MediaDownloadError("yt-dlp returned incomplete result metadata.")
    output_path = Path(values["path"]).expanduser().resolve()
    if not output_path.is_relative_to(output_directory) or not output_path.is_file():
        raise MediaDownloadError("yt-dlp returned an invalid output path.")
    return values["id"], values["title"], output_path


def _prepare_output_directory(path: Path) -> Path:
    directory = path.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _require_remote(kind: SourceKind) -> None:
    if kind is not SourceKind.REMOTE_URL:
        raise UnsupportedMediaError("yt-dlp command accepts remote URLs only.")


def _notify_started(callback: ProgressCallback | None) -> None:
    if callback is not None:
        callback(DownloadProgress(status=DownloadStatus.DOWNLOADING))


def _notify_completed(callback: ProgressCallback | None, path: Path, size: int) -> None:
    if callback is not None:
        callback(
            DownloadProgress(
                status=DownloadStatus.COMPLETED,
                downloaded_bytes=size,
                total_bytes=size,
                filename=str(path),
            )
        )
