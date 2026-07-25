"""Default worker composition."""

from pathlib import Path

from mevad.adapters import (
    FFmpegLoopMaker,
    FFmpegVideoCutter,
    YtDlpAudioExtractor,
    YtDlpVideoDownloader,
)
from mevad.jobs import JobService
from mevad_worker.executor import JobExecutor, WorkerDependencies
from mevad_worker.storage import WorkspaceManager


def create_default_executor(
    service: JobService,
    *,
    storage_root: Path = Path("storage/jobs"),
) -> JobExecutor:
    """Compose the production-intent worker adapters."""

    return JobExecutor(
        service=service,
        dependencies=WorkerDependencies(
            video_downloader=YtDlpVideoDownloader(),
            audio_extractor=YtDlpAudioExtractor(),
            video_cutter=FFmpegVideoCutter(),
            loop_maker=FFmpegLoopMaker(),
        ),
        workspaces=WorkspaceManager(storage_root),
    )
