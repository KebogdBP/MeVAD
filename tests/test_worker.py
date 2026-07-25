from pathlib import Path

import pytest

from mevad.audio import AudioExtractor
from mevad.cutter import VideoCutter
from mevad.downloader import CancellationToken, ProgressCallback, VideoDownloader
from mevad.exceptions import DownloadCancelledError, MediaProcessingError
from mevad.jobs import InMemoryJobRepository, Job, JobOperation, JobService, JobStatus
from mevad.loop_maker import LoopMaker
from mevad.models import (
    AudioExtractionRequest,
    AudioExtractionResult,
    DownloadProgress,
    DownloadStatus,
    LoopRenderRequest,
    LoopRenderResult,
    VideoCutRequest,
    VideoCutResult,
    VideoDownloadRequest,
    VideoDownloadResult,
)
from mevad_worker import JobExecutor, WorkerDependencies, WorkspaceManager


class FakeVideoDownloader(VideoDownloader):
    def download(
        self,
        request: VideoDownloadRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> VideoDownloadResult:
        assert cancellation is not None
        output_path = request.output_directory / "video.mp4"
        output_path.write_bytes(b"video")
        if on_progress is not None:
            on_progress(
                DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    downloaded_bytes=1,
                    total_bytes=2,
                )
            )
            on_progress(DownloadProgress(status=DownloadStatus.PROCESSING))
            on_progress(DownloadProgress(status=DownloadStatus.COMPLETED))
        return VideoDownloadResult(
            media_id="video-1",
            title="Video",
            output_path=output_path,
            filesize_bytes=5,
        )


class FakeAudioExtractor(AudioExtractor):
    def extract(
        self,
        request: AudioExtractionRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> AudioExtractionResult:
        assert cancellation is not None
        output_path = request.output_directory / f"audio.{request.codec.value}"
        output_path.write_bytes(b"audio")
        if on_progress is not None:
            on_progress(DownloadProgress(status=DownloadStatus.PROCESSING))
        return AudioExtractionResult(
            media_id="audio-1",
            title="Audio",
            codec=request.codec,
            output_path=output_path,
            filesize_bytes=5,
        )


class FakeVideoCutter(VideoCutter):
    def cut(
        self,
        request: VideoCutRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> VideoCutResult:
        assert request.input_path.is_file()
        assert cancellation is not None
        output_path = request.output_directory / "clip.mp4"
        output_path.write_bytes(b"clip")
        if on_progress is not None:
            on_progress(DownloadProgress(status=DownloadStatus.PROCESSING))
        return VideoCutResult(
            output_path=output_path,
            duration_seconds=request.interval.duration_seconds,
            filesize_bytes=4,
            mode=request.mode,
        )


class FakeLoopMaker(LoopMaker):
    def render(
        self,
        request: LoopRenderRequest,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation: CancellationToken | None = None,
    ) -> LoopRenderResult:
        assert request.input_path.is_file()
        assert cancellation is not None
        output_path = request.output_directory / f"loop.{request.output_format.value}"
        output_path.write_bytes(b"loop")
        if on_progress is not None:
            on_progress(DownloadProgress(status=DownloadStatus.PROCESSING))
        return LoopRenderResult(
            output_path=output_path,
            output_format=request.output_format,
            duration_seconds=request.output_duration_seconds,
            width=request.width,
            fps=request.fps,
            filesize_bytes=4,
        )


def test_executes_video_download_job(tmp_path: Path) -> None:
    service, executor = _executor(tmp_path)
    job = _create(
        service,
        JobOperation.DOWNLOAD_VIDEO,
        {"quality": "720p", "container": "mp4"},
    )

    completed = executor.execute(job.job_id)

    assert completed.status is JobStatus.SUCCEEDED
    assert completed.progress_percent == 100
    assert completed.result_reference == "job-1/results/video.mp4"
    assert (tmp_path / completed.result_reference).read_bytes() == b"video"


def test_executes_audio_extraction_job(tmp_path: Path) -> None:
    service, executor = _executor(tmp_path)
    job = _create(
        service,
        JobOperation.EXTRACT_AUDIO,
        {"codec": "opus", "bitrate": "192"},
    )

    completed = executor.execute(job.job_id)

    assert completed.status is JobStatus.SUCCEEDED
    assert completed.result_reference == "job-1/results/audio.opus"


def test_executes_staged_cut_and_removes_intermediate(tmp_path: Path) -> None:
    service, executor = _executor(tmp_path)
    job = _create(
        service,
        JobOperation.CUT_VIDEO,
        {
            "start_seconds": 1.0,
            "end_seconds": 3.0,
            "mode": "accurate",
        },
    )

    completed = executor.execute(job.job_id)

    assert completed.status is JobStatus.SUCCEEDED
    assert completed.result_reference == "job-1/results/clip.mp4"
    assert not (tmp_path / "job-1" / "intermediate").exists()


def test_executes_staged_loop_and_removes_intermediate(tmp_path: Path) -> None:
    service, executor = _executor(tmp_path)
    job = _create(
        service,
        JobOperation.MAKE_LOOP,
        {
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "output_format": "gif",
            "width": 480,
            "fps": 15,
            "quality": "balanced",
            "speed": "1",
            "repeat": True,
        },
    )

    completed = executor.execute(job.job_id)

    assert completed.status is JobStatus.SUCCEEDED
    assert completed.result_reference == "job-1/results/loop.gif"
    assert not (tmp_path / "job-1" / "intermediate").exists()


def test_invalid_worker_parameters_fail_safely(tmp_path: Path) -> None:
    service, executor = _executor(tmp_path)
    job = _create(
        service,
        JobOperation.DOWNLOAD_VIDEO,
        {"quality": "not-a-quality", "container": "mp4"},
    )

    failed = executor.execute(job.job_id)

    assert failed.status is JobStatus.FAILED
    assert failed.error_code == "job_execution_failed"
    assert failed.error_message == "The media job could not be completed."


def test_worker_acknowledges_concurrent_cancellation(tmp_path: Path) -> None:
    service = _service()

    class CancellingDownloader(FakeVideoDownloader):
        def download(
            self,
            request: VideoDownloadRequest,
            *,
            on_progress: ProgressCallback | None = None,
            cancellation: CancellationToken | None = None,
        ) -> VideoDownloadResult:
            service.cancel("job-1")
            assert cancellation is not None and cancellation.is_cancelled
            raise DownloadCancelledError("cancelled")

    executor = _executor(
        tmp_path,
        service=service,
        video_downloader=CancellingDownloader(),
    )[1]
    job = _create(
        service,
        JobOperation.DOWNLOAD_VIDEO,
        {"quality": "best", "container": "auto"},
    )

    cancelled = executor.execute(job.job_id)

    assert cancelled.status is JobStatus.CANCELLED


def test_workspace_rejects_unsafe_job_identifier(tmp_path: Path) -> None:
    manager = WorkspaceManager(tmp_path)

    with pytest.raises(MediaProcessingError, match="not safe"):
        manager.prepare("../escape")


def test_workspace_rejects_result_outside_storage(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-result.mp4"
    outside.write_bytes(b"outside")
    manager = WorkspaceManager(tmp_path)

    with pytest.raises(MediaProcessingError, match="escapes"):
        manager.result_reference(outside)


def _executor(
    storage_root: Path,
    *,
    service: JobService | None = None,
    video_downloader: VideoDownloader | None = None,
) -> tuple[JobService, JobExecutor]:
    selected_service = service or _service()
    executor = JobExecutor(
        selected_service,
        WorkerDependencies(
            video_downloader=video_downloader or FakeVideoDownloader(),
            audio_extractor=FakeAudioExtractor(),
            video_cutter=FakeVideoCutter(),
            loop_maker=FakeLoopMaker(),
        ),
        WorkspaceManager(storage_root),
    )
    return selected_service, executor


def _service() -> JobService:
    return JobService(
        InMemoryJobRepository(),
        job_id_factory=lambda: "job-1",
    )


def _create(
    service: JobService,
    operation: JobOperation,
    parameters: dict[str, str | int | float | bool],
) -> Job:
    return service.create(
        operation=operation,
        source_url="https://example.com/video",
        parameters=parameters,
    )
