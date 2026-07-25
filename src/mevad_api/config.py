"""Validated API configuration loaded from environment variables."""

from functools import lru_cache
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


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
