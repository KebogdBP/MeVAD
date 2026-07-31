"""FastAPI application factory."""

from fastapi import FastAPI

from mevad.adapters import YtDlpAnalyzer
from mevad.analyzer import MediaAnalyzer
from mevad.jobs import (
    InMemoryJobQueue,
    InMemoryJobRepository,
    JobQueue,
    JobService,
    SqlJobOutbox,
)
from mevad.jobs.redis_queue import RedisJobQueue
from mevad.jobs.sql_repository import SqlJobRepository
from mevad.runtime import RuntimeTools, discover_runtime_tools
from mevad_api.abuse import AbuseProtector, create_abuse_protector
from mevad_api.config import Settings, get_settings
from mevad_api.routes import health, jobs, media
from mevad_worker.storage import WorkspaceManager


def create_app(
    *,
    settings: Settings | None = None,
    analyzer: MediaAnalyzer | None = None,
    runtime_tools: RuntimeTools | None = None,
    job_service: JobService | None = None,
    job_queue: JobQueue | None = None,
    abuse_protector: AbuseProtector | None = None,
) -> FastAPI:
    """Create an isolated API application instance."""

    selected_settings = settings or get_settings()
    docs_url = "/docs" if selected_settings.api_docs_enabled else None
    openapi_url = "/openapi.json" if selected_settings.api_docs_enabled else None

    app = FastAPI(
        title=selected_settings.app_name,
        version=selected_settings.app_version,
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
    )
    app.state.settings = selected_settings
    app.state.media_analyzer = analyzer or YtDlpAnalyzer(
        proxy_url=selected_settings.media_proxy_url
    )
    app.state.runtime_tools = runtime_tools or discover_runtime_tools()
    selected_queue = job_queue or _create_queue(selected_settings)
    app.state.job_queue = selected_queue
    app.state.job_service = job_service or _create_job_service(selected_settings, selected_queue)
    app.state.workspace_manager = WorkspaceManager(selected_settings.storage_root)
    app.state.abuse_protector = abuse_protector or create_abuse_protector(selected_settings)
    app.router.add_event_handler("shutdown", app.state.job_service.close)
    app.router.add_event_handler("shutdown", app.state.abuse_protector.close)

    app.include_router(health.router)
    app.include_router(media.router, prefix=selected_settings.api_prefix)
    app.include_router(jobs.router, prefix=selected_settings.api_prefix)
    return app


def _create_queue(settings: Settings) -> JobQueue:
    if settings.queue_backend == "redis":
        return RedisJobQueue.from_url(
            settings.redis_url,
            queue_name=settings.redis_queue_name,
        )
    return InMemoryJobQueue()


def _create_job_service(settings: Settings, queue: JobQueue) -> JobService:
    if settings.job_backend == "postgres":
        repository = SqlJobRepository.from_url(settings.database_url)
        if settings.auto_create_schema:
            repository.create_schema()
        return JobService(
            repository,
            outbox=SqlJobOutbox(repository),
            default_max_attempts=settings.job_max_attempts,
            storage_retention_seconds=settings.storage_retention_seconds,
        )
    return JobService(
        InMemoryJobRepository(),
        queue=queue,
        default_max_attempts=settings.job_max_attempts,
        storage_retention_seconds=settings.storage_retention_seconds,
    )


app = create_app()
