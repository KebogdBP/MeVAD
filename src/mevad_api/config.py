"""Validated API configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

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
    network_sandbox: Literal["disabled", "external_proxy"] = "disabled"
    media_proxy_url: str | None = None
    job_backend: Literal["memory", "postgres"] = "memory"
    queue_backend: Literal["memory", "redis"] = "memory"
    database_url: str = "postgresql+psycopg://mevad:mevad@localhost:5432/mevad"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "mevad:jobs"
    abuse_protection_enabled: bool = False
    abuse_backend: Literal["memory", "redis"] = "memory"
    abuse_client_salt: str = "development-only-change-me"
    trust_proxy_headers: bool = False
    analyze_rate_limit: int = Field(default=10, ge=1, le=10000)
    analyze_rate_window_seconds: int = Field(default=60, ge=1, le=86400)
    job_create_rate_limit: int = Field(default=5, ge=1, le=10000)
    job_create_rate_window_seconds: int = Field(default=60, ge=1, le=86400)
    anonymous_active_job_limit: int = Field(default=2, ge=1, le=100)
    anonymous_job_slot_ttl_seconds: int = Field(default=10800, ge=60, le=86400)
    auto_create_schema: bool = False
    worker_poll_timeout_seconds: int = Field(default=5, ge=1, le=60)
    worker_media_timeout_seconds: int = Field(default=7200, ge=60, le=86400)
    worker_cpu_limit_seconds: int = Field(default=7200, ge=1, le=86400)
    worker_memory_limit_bytes: int = Field(
        default=2 * 1024 * 1024 * 1024,
        ge=64 * 1024 * 1024,
        le=128 * 1024 * 1024 * 1024,
    )
    worker_file_size_limit_bytes: int = Field(
        default=10 * 1024 * 1024 * 1024,
        ge=1024 * 1024,
        le=1024**5,
    )
    worker_open_files_limit: int = Field(default=256, ge=32, le=65536)
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
    storage_retention_seconds: int = Field(default=86400, ge=60, le=2592000)
    cleanup_poll_interval_seconds: float = Field(default=60, ge=0.1, le=3600)
    cleanup_lease_seconds: int = Field(default=300, ge=5, le=3600)
    cleanup_batch_size: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_worker_lease_timing(self) -> "Settings":
        if self.worker_heartbeat_seconds >= self.worker_lease_seconds:
            raise ValueError("Worker heartbeat interval must be shorter than its lease.")
        if self.worker_retry_max_seconds < self.worker_retry_base_seconds:
            raise ValueError("Worker retry maximum must not be shorter than its base.")
        if (
            self.environment == "production"
            and self.abuse_protection_enabled
            and len(self.abuse_client_salt) < 32
        ):
            raise ValueError("Production abuse client salt must be at least 32 characters.")
        if self.analyzer_enabled and self.network_sandbox != "external_proxy":
            raise ValueError("Enabled analyzer requires the external proxy network sandbox.")
        if self.network_sandbox == "external_proxy":
            if self.media_proxy_url is None:
                raise ValueError("External proxy network sandbox requires a media proxy URL.")
            parsed = urlsplit(self.media_proxy_url)
            if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
                raise ValueError("Media proxy URL must be an absolute HTTP(S) URL.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
