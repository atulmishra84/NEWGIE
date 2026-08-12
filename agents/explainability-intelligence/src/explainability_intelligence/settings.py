from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gie_env: str = "local"
    agent_name: str = "explainability-intelligence"
    agent_version: str = "1.0.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://gie:gie@localhost:5432/gie_explainability"
    redis_url: str = "redis://localhost:6379/7"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_events: str = "gie.explainability.events"
    jwt_secret: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    api_key_pepper: str = "local-pepper"
    require_auth: bool = True
    cache_ttl_seconds: int = 300
    otel_exporter_otlp_endpoint: str = ""

    # Anthropic Claude API
    anthropic_api_key: str = ""
    anthropic_model_id: str = "claude-opus-5"
    anthropic_max_tokens: int = 2048
    anthropic_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
