"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"


class SupabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = ""
    key: str = ""
    service_key: str = ""


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = "redis://localhost:6379/0"
    password: str = ""


class BullMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BULLMQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    queue_name: str = "aegis-scan"


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str = ""
    model: str = "gpt-4o-mini"


class Mem0Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEM0_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str = ""
    qdrant_host: str = ""
    qdrant_port: int = 6333


class RateLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    free: int = 10
    pro: int = 100
    enterprise: int = 1000


class ProcessingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    max_file_size_mb: int = Field(default=10, alias="MAX_FILE_SIZE_MB")
    processing_timeout_seconds: int = Field(default=30, alias="PROCESSING_TIMEOUT_SECONDS")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    embedding_cache_ttl: int = Field(default=3600, alias="EMBEDDING_CACHE_TTL")


class WebhookSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WEBHOOK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    secret: str = ""
    max_retries: int = 3
    retry_delay_seconds: int = 60


class AppConfig:
    def __init__(self) -> None:
        self.app = Settings()
        self.supabase = SupabaseSettings()
        self.redis = RedisSettings()
        self.bullmq = BullMQSettings()
        self.openai = OpenAISettings()
        self.mem0 = Mem0Settings()
        self.rate_limit = RateLimitSettings()
        self.processing = ProcessingSettings()
        self.webhook = WebhookSettings()

    @property
    def max_file_size_bytes(self) -> int:
        return self.processing.max_file_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
