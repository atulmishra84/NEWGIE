import pytest
from gie_contracts.knowledge import KnowledgeQueryRequest
from knowledge_intelligence.infrastructure.bootstrap import build_container
from knowledge_intelligence.settings import Settings


@pytest.mark.asyncio
async def test_empty_index_returns_empty_hits():
    settings = Settings(gie_env="test", require_auth=False)
    c = await build_container(memory=True, settings=settings)
    result = await c.query_engine.query(
        KnowledgeQueryRequest(query="anything"),
        tenant_id="t",
        correlation_id="c",
    )
    assert result.hits == []
    assert result.reasoning_path
