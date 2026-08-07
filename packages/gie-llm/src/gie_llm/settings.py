"""Bedrock configuration mixin — add to any agent's Settings class."""

from __future__ import annotations


class BedrockSettingsMixin:
    """Pydantic-settings mixin that adds Bedrock fields to any Settings class."""

    # AWS credentials (fall back to env / instance profile / ~/.aws)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_region: str = "us-east-1"

    # Bedrock inference
    bedrock_enabled: bool = True
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_max_tokens: int = 1024
    bedrock_temperature: float = 0.3

    # Titan Embeddings v2
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_embedding_dim: int = 512

    # Voice: STT via Amazon Transcribe, TTS via Amazon Polly
    bedrock_stt_enabled: bool = False   # requires S3 bucket
    bedrock_tts_enabled: bool = True
    aws_transcribe_bucket: str = ""     # S3 bucket for Transcribe jobs
    aws_polly_voice_id: str = "Joanna"
    aws_polly_engine: str = "neural"
