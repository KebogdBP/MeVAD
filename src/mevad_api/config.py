"""Validated API configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
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
    worker_media_timeout_seconds: int = Field(default=7200, ge=60, le=86400)
    worker_id: str | None = Field(default=None, min_length=1, max_length=128)
    worker_lease_seconds: int = Field(default=60, ge=5, le=3600)
    worker_heartbeat_seconds: int = Field(default=15, ge=1, le=300)
    worker_recovery_interval_seconds: int = Field(default=30, ge=5, le=600)
    worker_claim_stale_seconds: int = Field(default=120, ge=30, le=3600)
    worker_retry_base_seconds: int = Field(default=5, ge=1, le=3600)
    worker_retry_max_seconds: int = Field(default=300, ge=1, le=86400)
    outbox_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)
    outbox_lease_seconds: int = Field(default=30, ge=5, le=3600)
    outbox_batch_size: int = Field(default=100, ge=1, le=1000)
    job_max_attempts: int = Field(default=3, ge=1, le=10)
    storage_root: Path = Path("storage/jobs")

    @model_validator(mode="after")
    def validate_worker_lease_timing(self) -> "Settings":
        if self.worker_heartbeat_seconds >= self.worker_lease_seconds:
            raise ValueError("Worker heartbeat interval must be shorter than its lease.")
        if self.worker_retry_max_seconds < self.worker_retry_base_seconds:
            raise ValueError("Worker retry maximum must not be shorter than its base.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
