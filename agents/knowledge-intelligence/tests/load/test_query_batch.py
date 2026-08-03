import pytest
from gie_contracts.knowledge import KnowledgeQueryRequest


@pytest.mark.asyncio
async def test_batch_queries(container):
    for i in range(20):
        result = await container.query_engine.query(
            KnowledgeQueryRequest(query=f"guardrail template {i}", top_k=3),
            tenant_id="load",
            correlation_id=f"c{i}",
        )
        assert result.took_ms >= 0
