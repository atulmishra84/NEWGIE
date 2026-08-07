"""AWS Bedrock Titan Embeddings V2 embedding service."""

from __future__ import annotations

from gie_llm import BedrockEmbeddingClient
from knowledge_intelligence.domain.ports import EmbeddingService


class BedrockEmbeddingService(EmbeddingService):
    """Production embedding service backed by Amazon Titan Embeddings V2."""

    def __init__(
        self,
        *,
        region: str = "us-east-1",
        model_id: str = "amazon.titan-embed-text-v2:0",
        dimensions: int = 512,
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        aws_session_token: str = "",
    ) -> None:
        self._client = BedrockEmbeddingClient(
            region=region,
            model_id=model_id,
            dimensions=dimensions,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )
        self._dim = dimensions

    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._client.embed(texts)
