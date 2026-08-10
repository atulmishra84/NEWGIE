"""Twelve-factor configuration for Knowledge Intelligence Agent."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gie_env: str = "local"
    agent_name: str = "knowledge-intelligence"
    agent_version: str = "1.0.0"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://gie:gie@localhost:5432/gie_knowledge"
    redis_url: str = "redis://localhost:6379/1"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "giepassword"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "knowledge_embeddings"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_events: str = "gie.knowledge.events"
    kafka_topic_commands: str = "gie.knowledge.commands"

    jwt_secret: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    api_key_pepper: str = "local-pepper"
    require_auth: bool = True

    embedding_dim: int = 384
    embedding_model: str = (
        "hash-v1"  # deterministic local embedder; swap for vendor models
    )
    default_top_k: int = 10
    cache_ttl_seconds: int = 300
    rate_limit_per_minute: int = 120
    scan_workspace_root: str = "/tmp/gie-knowledge"

    flag_enable_cloud_embeddings: bool = False
    flag_enable_reindex_on_start: bool = True
    flag_enable_graph_expansion: bool = True

    otel_exporter_otlp_endpoint: str = ""
    seed_data_path: str = ""  # resolved relative to package if empty

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # AWS Bedrock LLM
    bedrock_enabled: bool = True
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_max_tokens: int = 1024
    bedrock_temperature: float = 0.3
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_embedding_dim: int = 512
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
