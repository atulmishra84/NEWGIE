from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gie_env: str = "local"
    agent_name: str = "integration-intelligence"
    agent_version: str = "1.0.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://gie:gie@localhost:5432/gie_integration"
    redis_url: str = "redis://localhost:6379/10"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_events: str = "gie.integration.events"
    jwt_secret: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    api_key_pepper: str = "local-pepper"
    require_auth: bool = True
    cache_ttl_seconds: int = 300
    otel_exporter_otlp_endpoint: str = ""
    circuit_failure_threshold: int = 5
    circuit_open_seconds: int = 60
    retry_max_attempts: int = 3
    retry_base_delay_ms: int = 100
    webhook_hmac_secret: str = "local-webhook-secret"
    mtls_enabled: bool = False

    # AWS Bedrock LLM
    bedrock_enabled: bool = True
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_max_tokens: int = 1024
    bedrock_temperature: float = 0.3
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
