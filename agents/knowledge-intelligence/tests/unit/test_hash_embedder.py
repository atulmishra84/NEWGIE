import pytest

from knowledge_intelligence.infrastructure.embeddings.hash_embedder import (
    HashEmbeddingService,
)


@pytest.mark.asyncio
async def test_embed_deterministic_and_normalized():
    svc = HashEmbeddingService(dim=64)
    a = (await svc.embed(["prompt injection attack"]))[0]
    b = (await svc.embed(["prompt injection attack"]))[0]
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6
