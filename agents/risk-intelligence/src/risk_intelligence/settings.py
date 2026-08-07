from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gie_env: str = "local"
    agent_name: str = "risk-intelligence"
    agent_version: str = "1.0.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://gie:gie@localhost:5432/gie_risk"
    redis_url: str = "redis://localhost:6379/3"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_events: str = "gie.risk.events"
    kafka_topic_commands: str = "gie.risk.commands"
    jwt_secret: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    api_key_pepper: str = "local-pepper"
    require_auth: bool = True
    cache_ttl_seconds: int = 300
    rate_limit_per_minute: int = 60
    default_risk_model_id: str = "default-v1"
    otel_exporter_otlp_endpoint: str = ""


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
