from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gie_env: str = "local"
    agent_name: str = "orchestrator"
    agent_version: str = "1.0.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://gie:gie@localhost:5432/gie_orchestrator"
    redis_url: str = "redis://localhost:6379/11"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_events: str = "gie.orchestrator.events"
    jwt_secret: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    api_key_pepper: str = "local-pepper"
    require_auth: bool = True
    cache_ttl_seconds: int = 600
    otel_exporter_otlp_endpoint: str = ""
    default_step_timeout_ms: int = 45_000
    default_retries: int = 2
    retry_base_delay_ms: int = 50
    max_parallel_steps: int = 8
    simulate_agents: bool = True  # local/test: no real HTTP to peer agents
    context_url: str = "http://localhost:8080"
    knowledge_url: str = "http://localhost:8081"
    policy_url: str = "http://localhost:8082"
    risk_url: str = "http://localhost:8083"
    compliance_url: str = "http://localhost:8084"
    recommendation_url: str = "http://localhost:8085"
    generator_url: str = "http://localhost:8086"
    explainability_url: str = "http://localhost:8087"
    validation_url: str = "http://localhost:8088"
    learning_url: str = "http://localhost:8089"
    integration_url: str = "http://localhost:8090"

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
