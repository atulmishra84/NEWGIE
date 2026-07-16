"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    gie_env: Literal["local", "dev", "staging", "prod"] = "local"
    agent_version: str = Field(default="1.0.0", alias="AGENT_VERSION")
    agent_name: str = "context-intelligence"

    database_url: str = Field(
        default="postgresql+asyncpg://gie:gie@localhost:5432/gie_context",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="giepassword", alias="NEO4J_PASSWORD")

    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="gie_evidence", alias="QDRANT_COLLECTION")

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_scan_topic: str = Field(default="gie.context.scans", alias="KAFKA_SCAN_TOPIC")
    kafka_events_topic: str = Field(
        default="gie.context.events",
        alias="KAFKA_EVENTS_TOPIC",
    )

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="gie", alias="JWT_ISSUER")
    api_key_pepper: str = Field(default="change-me", alias="API_KEY_PEPPER")

    flag_enable_cloud_scanners: bool = Field(
        default=False,
        alias="FLAG_ENABLE_CLOUD_SCANNERS",
    )
    scan_timeout_seconds: int = Field(default=300, alias="SCAN_TIMEOUT_SECONDS")
    scan_max_file_bytes: int = Field(default=1_048_576, alias="SCAN_MAX_FILE_BYTES")
    scan_max_files: int = Field(default=10_000, alias="SCAN_MAX_FILES")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    workspace_root: str = Field(default="/tmp/gie-scans", alias="WORKSPACE_ROOT")
    max_concurrent_scans: int = Field(default=4, alias="MAX_CONCURRENT_SCANS")

    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    json_logs: bool = Field(default=True, alias="JSON_LOGS")

    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")

    @property
    def effective_celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def effective_celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
