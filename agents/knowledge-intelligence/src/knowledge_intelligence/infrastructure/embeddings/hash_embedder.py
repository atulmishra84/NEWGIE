"""Deterministic local embedding service (vendor-neutral, no external API required).

Produces fixed-dimension vectors via hashed n-grams. Suitable for tests and local
dev; swap for OpenAI/Azure/Bedrock embedders behind the same EmbeddingService port.
"""

from __future__ import annotations

import hashlib
import math
import re

from knowledge_intelligence.domain.ports import EmbeddingService


_TOKEN = re.compile(r"[a-z0-9_]+", re.I)


class HashEmbeddingService(EmbeddingService):
    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = _TOKEN.findall(text.lower())
        if not tokens:
            return vec
        for tok in tokens:
            digest = hashlib.sha256(tok.encode()).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
            # bigrams
        for a, b in zip(tokens, tokens[1:]):
            digest = hashlib.sha256(f"{a}_{b}".encode()).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += 0.5 * sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
