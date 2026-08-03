from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gie_env: str = "local"
    agent_name: str = "policy-intelligence"
    agent_version: str = "1.0.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://gie:gie@localhost:5432/gie_policy"
    redis_url: str = "redis://localhost:6379/2"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "giepassword"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_events: str = "gie.policy.events"
    kafka_topic_commands: str = "gie.policy.commands"
    jwt_secret: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    api_key_pepper: str = "local-pepper"
    require_auth: bool = True
    cache_ttl_seconds: int = 300
    rate_limit_per_minute: int = 60
    knowledge_base_url: str = "http://localhost:8081"
    flag_call_knowledge_agent: bool = False
    otel_exporter_otlp_endpoint: str = ""

@lru_cache
def get_settings() -> Settings:
    return Settings()
