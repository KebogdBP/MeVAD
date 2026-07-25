"""Synchronous job executor intended to run outside the API process."""

from dataclasses import dataclass
from pathlib import Path

from mevad.audio import AudioExtractor
from mevad.cutter import VideoCutter
from mevad.downloader import CancellationToken, VideoDownloader
from mevad.exceptions import (
    DownloadCancelledError,
    MeVADError,
)
from mevad.jobs import Job, JobOperation, JobService, JobStatus
from mevad.jobs.models import JobParameter
from mevad.loop_maker import LoopMaker
from mevad.models import (
    AudioBitrate,
    AudioCodec,
    AudioExtractionRequest,
    ClipInterval,
    CutMode,
    DownloadProgress,
    DownloadStatus,
    LoopFormat,
    LoopQuality,
    LoopRenderRequest,
    MediaSource,
    PlaybackSpeed,
    SourceKind,
    VideoContainer,
    VideoCutRequest,
    VideoDownloadRequest,
    VideoQuality,
)
from mevad_worker.storage import JobWorkspace, WorkspaceManager


@dataclass(frozen=True, slots=True)
class WorkerDependencies:
    """Core operation adapters used by the worker."""

    video_downloader: VideoDownloader
    audio_extractor: AudioExtractor
    video_cutter: VideoCutter
    loop_maker: LoopMaker


class JobCancellationToken(CancellationToken):
    """Cancellation view backed by durable job state."""

    def __init__(self, service: JobService, job_id: str) -> None:
        self._service = service
        self._job_id = job_id

    @property
    def is_cancelled(self) -> bool:
        return self._service.get(self._job_id).status in {
            JobStatus.CANCEL_REQUESTED,
            JobStatus.CANCELLED,
        }


class ProgressBridge:
    """Map core progress events to monotonic job percentages."""

    def __init__(
        self,
        service: JobService,
        job_id: str,
        *,
        base_percent: int,
        span_percent: int,
    ) -> None:
        self._service = service
        self._job_id = job_id
        self._base = base_percent
        self._span = span_percent

    def __call__(self, progress: DownloadProgress) -> None:
        job = self._service.get(self._job_id)
        if job.status in {JobStatus.CANCEL_REQUESTED, JobStatus.CANCELLED}:
            return
        if progress.status is DownloadStatus.PROCESSING and job.status is JobStatus.RUNNING:
            job = self._service.mark_processing(self._job_id)

        candidate = self._candidate(progress)
        if candidate > job.progress_percent and candidate <= 99:
            self._service.report_progress(self._job_id, candidate)

    def _candidate(self, progress: DownloadProgress) -> int:
        if progress.status is DownloadStatus.DOWNLOADING:
            fraction = progress.fraction or 0.01
            return self._base + max(1, int(fraction * self._span))
        if progress.status is DownloadStatus.PROCESSING:
            return self._base + max(1, int(self._span * 0.9))
        return self._base + self._span


class JobExecutor:
    """Execute one already-persisted queued job synchronously."""

    def __init__(
        self,
        service: JobService,
        dependencies: WorkerDependencies,
        workspaces: WorkspaceManager,
    ) -> None:
        self._service = service
        self._dependencies = dependencies
        self._workspaces = workspaces

    def execute(self, job_id: str) -> Job:
        job = self._service.start(job_id)
        token = JobCancellationToken(self._service, job_id)
        workspace: JobWorkspace | None = None
        staged_operation = job.operation in {JobOperation.CUT_VIDEO, JobOperation.MAKE_LOOP}

        try:
            workspace = self._workspaces.prepare(job_id)
            output_path = self._dispatch(job, workspace, token)
            reference = self._workspaces.result_reference(output_path)
            return self._service.succeed(job_id, result_reference=reference)
        except DownloadCancelledError:
            return self._finish_cancellation(job_id)
        except (MeVADError, KeyError, TypeError, ValueError):
            current = self._service.get(job_id)
            if current.status is JobStatus.CANCEL_REQUESTED:
                return self._service.acknowledge_cancellation(job_id)
            return self._service.fail(
                job_id,
                error_code="job_execution_failed",
                error_message="The media job could not be completed.",
            )
        finally:
            if staged_operation and workspace is not None:
                self._workspaces.cleanup_intermediate(workspace)

    def _dispatch(
        self,
        job: Job,
        workspace: JobWorkspace,
        token: JobCancellationToken,
    ) -> Path:
        if job.operation is JobOperation.DOWNLOAD_VIDEO:
            return self._download_video(job, workspace.results, token, stage=(0, 100))
        if job.operation is JobOperation.EXTRACT_AUDIO:
            return self._extract_audio(job, workspace.results, token)

        source_path = self._download_video(
            job,
            workspace.intermediate,
            token,
            stage=(0, 50),
            quality=VideoQuality.BEST,
            container=VideoContainer.AUTO,
        )
        if job.operation is JobOperation.CUT_VIDEO:
            return self._cut_video(job, source_path, workspace.results, token)
        if job.operation is JobOperation.MAKE_LOOP:
            return self._make_loop(job, source_path, workspace.results, token)
        raise ValueError(f"Unsupported job operation: {job.operation}")

    def _download_video(
        self,
        job: Job,
        output_directory: Path,
        token: JobCancellationToken,
        *,
        stage: tuple[int, int],
        quality: VideoQuality | None = None,
        container: VideoContainer | None = None,
    ) -> Path:
        selected_quality = quality or VideoQuality(_string_parameter(job, "quality"))
        selected_container = container or VideoContainer(_string_parameter(job, "container"))
        result = self._dependencies.video_downloader.download(
            VideoDownloadRequest(
                source=_source(job),
                output_directory=output_directory,
                quality=selected_quality,
                container=selected_container,
            ),
            on_progress=ProgressBridge(
                self._service,
                job.job_id,
                base_percent=stage[0],
                span_percent=stage[1],
            ),
            cancellation=token,
        )
        return result.output_path

    def _extract_audio(
        self,
        job: Job,
        output_directory: Path,
        token: JobCancellationToken,
    ) -> Path:
        result = self._dependencies.audio_extractor.extract(
            AudioExtractionRequest(
                source=_source(job),
                output_directory=output_directory,
                codec=AudioCodec(_string_parameter(job, "codec")),
                bitrate=AudioBitrate(_string_parameter(job, "bitrate")),
            ),
            on_progress=ProgressBridge(
                self._service,
                job.job_id,
                base_percent=0,
                span_percent=100,
            ),
            cancellation=token,
        )
        return result.output_path

    def _cut_video(
        self,
        job: Job,
        source_path: Path,
        output_directory: Path,
        token: JobCancellationToken,
    ) -> Path:
        result = self._dependencies.video_cutter.cut(
            VideoCutRequest(
                input_path=source_path,
                output_directory=output_directory,
                interval=_interval(job),
                mode=CutMode(_string_parameter(job, "mode")),
            ),
            on_progress=ProgressBridge(
                self._service,
                job.job_id,
                base_percent=50,
                span_percent=50,
            ),
            cancellation=token,
        )
        return result.output_path

    def _make_loop(
        self,
        job: Job,
        source_path: Path,
        output_directory: Path,
        token: JobCancellationToken,
    ) -> Path:
        result = self._dependencies.loop_maker.render(
            LoopRenderRequest(
                input_path=source_path,
                output_directory=output_directory,
                interval=_interval(job),
                output_format=LoopFormat(_string_parameter(job, "output_format")),
                width=_int_parameter(job, "width"),
                fps=_int_parameter(job, "fps"),
                quality=LoopQuality(_string_parameter(job, "quality")),
                speed=PlaybackSpeed(_string_parameter(job, "speed")),
                repeat=_bool_parameter(job, "repeat"),
            ),
            on_progress=ProgressBridge(
                self._service,
                job.job_id,
                base_percent=50,
                span_percent=50,
            ),
            cancellation=token,
        )
        return result.output_path

    def _finish_cancellation(self, job_id: str) -> Job:
        current = self._service.get(job_id)
        if current.status is JobStatus.CANCEL_REQUESTED:
            return self._service.acknowledge_cancellation(job_id)
        if current.status is JobStatus.CANCELLED:
            return current
        return self._service.fail(
            job_id,
            error_code="job_cancelled",
            error_message="The media operation was cancelled.",
        )


def _source(job: Job) -> MediaSource:
    return MediaSource(kind=SourceKind.REMOTE_URL, value=job.source_url)


def _interval(job: Job) -> ClipInterval:
    return ClipInterval(
        start_seconds=_float_parameter(job, "start_seconds"),
        end_seconds=_float_parameter(job, "end_seconds"),
    )


def _parameter(job: Job, key: str) -> JobParameter:
    try:
        return job.parameters[key]
    except KeyError as error:
        raise KeyError(f"Missing job parameter: {key}") from error


def _string_parameter(job: Job, key: str) -> str:
    value = _parameter(job, key)
    if not isinstance(value, str):
        raise TypeError(f"Job parameter {key} must be a string.")
    return value


def _int_parameter(job: Job, key: str) -> int:
    value = _parameter(job, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Job parameter {key} must be an integer.")
    return value


def _float_parameter(job: Job, key: str) -> float:
    value = _parameter(job, key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"Job parameter {key} must be numeric.")
    return float(value)


def _bool_parameter(job: Job, key: str) -> bool:
    value = _parameter(job, key)
    if not isinstance(value, bool):
        raise TypeError(f"Job parameter {key} must be boolean.")
    return value
