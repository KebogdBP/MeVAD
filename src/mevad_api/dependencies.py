"""FastAPI dependencies backed by app-local services."""

from typing import Annotated, cast

from fastapi import Depends, Request

from mevad.analyzer import MediaAnalyzer
from mevad.runtime import RuntimeTools
from mevad_api.config import Settings


def get_app_settings(request: Request) -> Settings:
    """Get settings selected by the application factory."""

    return cast(Settings, request.app.state.settings)


def get_media_analyzer(request: Request) -> MediaAnalyzer:
    """Get the configured analyzer adapter."""

    return cast(MediaAnalyzer, request.app.state.media_analyzer)


def get_runtime_tools(request: Request) -> RuntimeTools:
    """Get runtime tool discovery captured at application startup."""

    return cast(RuntimeTools, request.app.state.runtime_tools)


SettingsDependency = Annotated[Settings, Depends(get_app_settings)]
AnalyzerDependency = Annotated[MediaAnalyzer, Depends(get_media_analyzer)]
RuntimeToolsDependency = Annotated[RuntimeTools, Depends(get_runtime_tools)]
