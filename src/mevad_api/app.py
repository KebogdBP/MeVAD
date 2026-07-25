"""FastAPI application factory."""

from fastapi import FastAPI

from mevad.adapters import YtDlpAnalyzer
from mevad.analyzer import MediaAnalyzer
from mevad.jobs import InMemoryJobRepository, JobService
from mevad.runtime import RuntimeTools, discover_runtime_tools
from mevad_api.config import Settings, get_settings
from mevad_api.routes import health, jobs, media


def create_app(
    *,
    settings: Settings | None = None,
    analyzer: MediaAnalyzer | None = None,
    runtime_tools: RuntimeTools | None = None,
    job_service: JobService | None = None,
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
    app.state.media_analyzer = analyzer or YtDlpAnalyzer()
    app.state.runtime_tools = runtime_tools or discover_runtime_tools()
    app.state.job_service = job_service or JobService(InMemoryJobRepository())

    app.include_router(health.router)
    app.include_router(media.router, prefix=selected_settings.api_prefix)
    app.include_router(jobs.router, prefix=selected_settings.api_prefix)
    return app


app = create_app()
