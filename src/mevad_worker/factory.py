"""Default worker composition."""

from pathlib import Path

from mevad.adapters import (
    FFmpegLoopMaker,
    FFmpegVideoCutter,
    YtDlpCommandAudioExtractor,
    YtDlpCommandVideoDownloader,
)
from mevad.adapters.process import ProcessLimits, limited_process_runner
from mevad.jobs import JobService
from mevad_worker.executor import JobExecutor, WorkerDependencies
from mevad_worker.storage import WorkspaceManager


def create_default_executor(
    service: JobService,
    *,
    storage_root: Path = Path("storage/jobs"),
    media_timeout_seconds: float = 7200,
    worker_id: str | None = None,
    lease_duration_seconds: int = 60,
    heartbeat_interval_seconds: int = 15,
    process_limits: ProcessLimits | None = None,
    media_proxy_url: str | None = None,
) -> JobExecutor:
    """Compose the production-intent worker adapters."""

    runner = limited_process_runner(process_limits or ProcessLimits())
    return JobExecutor(
        service=service,
        dependencies=WorkerDependencies(
            video_downloader=YtDlpCommandVideoDownloader(
                timeout_seconds=media_timeout_seconds,
                runner=runner,
                proxy_url=media_proxy_url,
            ),
            audio_extractor=YtDlpCommandAudioExtractor(
                timeout_seconds=media_timeout_seconds,
                runner=runner,
                proxy_url=media_proxy_url,
            ),
            video_cutter=FFmpegVideoCutter(runner=runner),
            loop_maker=FFmpegLoopMaker(runner=runner),
        ),
        workspaces=WorkspaceManager(storage_root),
        worker_id=worker_id,
        lease_duration_seconds=lease_duration_seconds,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
    )
