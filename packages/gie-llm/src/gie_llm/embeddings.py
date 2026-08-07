"""AWS Bedrock Titan Embeddings client."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from typing import Any

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bedrock-embed")


class BedrockEmbeddingClient:
    """Async wrapper around Titan Embeddings V2 via bedrock-runtime."""

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
        self._region = region
        self._model_id = model_id
        self._dimensions = dimensions
        self._creds: dict[str, str] = {}
        if aws_access_key_id:
            self._creds["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            self._creds["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            self._creds["aws_session_token"] = aws_session_token

    @cached_property
    def _boto_client(self) -> Any:
        import boto3
        return boto3.client("bedrock-runtime", region_name=self._region, **self._creds)

    def dimension(self) -> int:
        return self._dimensions

    def _embed_one_sync(self, text: str) -> list[float]:
        body = json.dumps({
            "inputText": text[:8192],
            "dimensions": self._dimensions,
            "normalize": True,
        })
        resp = self._boto_client.invoke_model(
            modelId=self._model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(resp["body"].read())
        return list(result["embedding"])

    async def embed(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        results: list[list[float]] = []
        for text in texts:
            try:
                vec = await loop.run_in_executor(_EXECUTOR, self._embed_one_sync, text)
                results.append(vec)
            except Exception as exc:
                logger.warning("Bedrock embedding failed for text: %s", exc)
                results.append([0.0] * self._dimensions)
        return results
