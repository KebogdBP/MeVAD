"""Validated API configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MeVAD API settings."""

    model_config = SettingsConfigDict(
        env_prefix="MEVAD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MeVAD API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_docs_enabled: bool = True
    require_media_tools: bool = True
    analyzer_enabled: bool = False
    job_backend: Literal["memory", "postgres"] = "memory"
    queue_backend: Literal["memory", "redis"] = "memory"
    database_url: str = "postgresql+psycopg://mevad:mevad@localhost:5432/mevad"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "mevad:jobs"
    auto_create_schema: bool = False
    worker_poll_timeout_seconds: int = Field(default=5, ge=1, le=60)
    job_max_attempts: int = Field(default=3, ge=1, le=10)
    storage_root: Path = Path("storage/jobs")


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
