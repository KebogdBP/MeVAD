"""yt-dlp adapter for bounded single-video downloads."""

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Protocol, TypeAlias, cast

from mevad.downloader import (
    CancellationToken,
    ProgressCallback,
    VideoDownloader,
    build_video_format_selector,
)
from mevad.exceptions import (
    DownloadCancelledError,
    MediaDownloadError,
    UnsupportedMediaError,
)
from mevad.models import (
    DownloadProgress,
    DownloadStatus,
    SourceKind,
    VideoContainer,
    VideoDownloadRequest,
    VideoDownloadResult,
)
from mevad.security import normalize_remote_url

Info: TypeAlias = Mapping[str, Any]
HookData: TypeAlias = Mapping[str, Any]
Hook: TypeAlias = Callable[[HookData], None]


class DownloadClient(Protocol):
    """Small YoutubeDL subset required for downloads."""

    def extract_info(self, url: str, *, download: bool) -> Info | None:
        """Download and return metadata for one URL."""
        ...


ClientContext: TypeAlias = AbstractContextManager[DownloadClient]
ClientFactory: TypeAlias = Callable[[Mapping[str, Any]], ClientContext]


class YtDlpVideoDownloader(VideoDownloader):
    """Download one remote video through yt-dlp."""

    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or _default_client_factory

    def download(
        self,
        request: VideoDownloadRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> VideoDownloadResult:
        if request.source.kind is not SourceKind.REMOTE_URL:
            raise UnsupportedMediaError("yt-dlp downloader accepts remote URLs only.")
        if cancellation is not None and cancellation.is_cancelled:
            raise DownloadCancelledError("Download was cancelled.")

        normalized_url = normalize_remote_url(request.source.value)
        output_directory = request.output_directory.expanduser().resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        final_path: Path | None = None

        def progress_hook(data: HookData) -> None:
            nonlocal final_path
            _raise_if_cancelled(cancellation)
            progress = _normalize_progress(data)
            if progress is not None:
                if progress.filename:
                    final_path = Path(progress.filename)
                if on_progress is not None:
                    on_progress(progress)

        def postprocessor_hook(data: HookData) -> None:
            nonlocal final_path
            _raise_if_cancelled(cancellation)
            info = data.get("info_dict")
            if isinstance(info, Mapping):
                filepath = _optional_text(info.get("filepath"))
                if filepath:
                    final_path = Path(filepath)
            if on_progress is not None and data.get("status") == "finished":
                on_progress(
                    DownloadProgress(
                        status=DownloadStatus.PROCESSING,
                        filename=str(final_path) if final_path else None,
                    )
                )

        options = _build_options(
            request=request,
            output_directory=output_directory,
            progress_hook=progress_hook,
            postprocessor_hook=postprocessor_hook,
        )

        try:
            with self._client_factory(options) as client:
                info = client.extract_info(normalized_url, download=True)
        except DownloadCancelledError:
            raise
        except Exception as error:
            if cancellation is not None and cancellation.is_cancelled:
                raise DownloadCancelledError("Download was cancelled.") from error
            raise MediaDownloadError(_safe_error_message(error)) from error

        if info is None:
            raise MediaDownloadError("yt-dlp returned no download metadata.")
        media_id = _required_text(info, "id")
        title = _required_text(info, "title")
        final_path = final_path or _path_from_info(info)
        if final_path is None:
            raise MediaDownloadError("yt-dlp returned no output path.")

        safe_path = _ensure_output_path(final_path, output_directory)
        if not safe_path.is_file():
            raise MediaDownloadError("Downloaded output file was not found.")

        result = VideoDownloadResult(
            media_id=media_id,
            title=title,
            output_path=safe_path,
            filesize_bytes=safe_path.stat().st_size,
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


def _default_client_factory(options: Mapping[str, Any]) -> ClientContext:
    import yt_dlp  # type: ignore[import-untyped]

    return cast(ClientContext, yt_dlp.YoutubeDL(dict(options)))


def _build_options(
    *,
    request: VideoDownloadRequest,
    output_directory: Path,
    progress_hook: Hook,
    postprocessor_hook: Hook,
) -> Mapping[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": build_video_format_selector(request.quality, request.container),
        "paths": {"home": str(output_directory)},
        "outtmpl": {"default": "%(title).180B [%(id)s].%(ext)s"},
        "windowsfilenames": True,
        "trim_file_name": 220,
        "overwrites": False,
        "continuedl": True,
        "nopart": False,
        "socket_timeout": 15,
        "retries": 2,
        "fragment_retries": 2,
        "extractor_retries": 1,
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [postprocessor_hook],
    }
    if request.container is not VideoContainer.AUTO:
        options["merge_output_format"] = request.container.value
    return options


def _normalize_progress(data: HookData) -> DownloadProgress | None:
    status = data.get("status")
    if status == "downloading":
        return DownloadProgress(
            status=DownloadStatus.DOWNLOADING,
            downloaded_bytes=_optional_integer(data.get("downloaded_bytes")),
            total_bytes=_optional_integer(data.get("total_bytes"))
            or _optional_integer(data.get("total_bytes_estimate")),
            speed_bytes_per_second=_optional_number(data.get("speed")),
            eta_seconds=_optional_number(data.get("eta")),
            filename=_optional_text(data.get("filename")),
        )
    if status == "finished":
        return DownloadProgress(
            status=DownloadStatus.PROCESSING,
            downloaded_bytes=_optional_integer(data.get("downloaded_bytes")),
            total_bytes=_optional_integer(data.get("total_bytes")),
            filename=_optional_text(data.get("filename")),
        )
    return None


def _raise_if_cancelled(cancellation: CancellationToken | None) -> None:
    if cancellation is not None and cancellation.is_cancelled:
        raise DownloadCancelledError("Download was cancelled.")


def _path_from_info(info: Info) -> Path | None:
    filepath = _optional_text(info.get("filepath")) or _optional_text(info.get("_filename"))
    return Path(filepath) if filepath else None


def _ensure_output_path(path: Path, output_directory: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_relative_to(output_directory):
        raise MediaDownloadError("yt-dlp returned a path outside the output directory.")
    return resolved


def _required_text(info: Info, key: str) -> str:
    value = _optional_text(info.get(key))
    if value is None:
        raise MediaDownloadError(f"Download metadata has no {key}.")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _optional_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _safe_error_message(error: Exception) -> str:
    message = str(error).strip()
    return f"Media download failed: {message or type(error).__name__}"
