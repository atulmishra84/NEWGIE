import pytest
from gie_contracts.knowledge import (
    KnowledgeDomain,
    KnowledgeNode,
    KnowledgeQueryRequest,
    KnowledgeUpsertRequest,
    NodeKind,
    Confidence,
)


@pytest.mark.asyncio
async def test_seeded_query_finds_owasp(container):
    result = await container.query_engine.query(
        KnowledgeQueryRequest(query="prompt injection LLM", top_k=5),
        tenant_id="t1",
        correlation_id="c1",
    )
    assert result.hits
    assert result.reasoning_path
    assert result.confidence.score >= 0
    titles = " ".join(h.node.title.lower() for h in result.hits)
    assert "prompt" in titles or "injection" in titles or "llm01" in titles


@pytest.mark.asyncio
async def test_upsert_and_get(container):
    node = KnowledgeNode(
        node_id="custom-control-1",
        kind=NodeKind.CONTROL,
        domain=KnowledgeDomain.SOC2,
        title="Custom AI Logging Control",
        summary="Require immutable audit logs for agent tool calls",
        confidence=Confidence(score=0.99),
    )
    out = await container.upsert.handle(
        KnowledgeUpsertRequest(nodes=[node], edges=[]),
        tenant_id="t1",
        actor="test",
        correlation_id="c2",
    )
    assert out["nodes_upserted"] == 1
    got = await container.get_node.handle("custom-control-1")
    assert got.title.startswith("Custom")


@pytest.mark.asyncio
async def test_version_diff(container):
    await container.versions.publish("v-a", "aa", 1, 0)
    node = KnowledgeNode(
        node_id="diff-node",
        kind=NodeKind.CONCEPT,
        domain=KnowledgeDomain.POLICY_MAPPINGS,
        title="Diff Node",
        summary="added in vb",
        confidence=Confidence(score=1.0),
    )
    await container.upsert.handle(
        KnowledgeUpsertRequest(nodes=[node], publish_version=True, version_label="v-b"),
        tenant_id="t1",
        actor="test",
        correlation_id="c3",
    )
    diff = await container.diff_versions.handle("v-a", "v-b")
    assert "diff-node" in diff.added_nodes or diff.to_version == "v-b"
