from gie_contracts.knowledge import KnowledgeDomain, KnowledgeNode, NodeKind, Confidence


def test_knowledge_node_roundtrip():
    node = KnowledgeNode(
        node_id="t1",
        kind=NodeKind.THREAT,
        domain=KnowledgeDomain.OWASP_LLM,
        title="Test",
        summary="Summary",
        confidence=Confidence(score=0.9),
    )
    data = node.model_dump()
    again = KnowledgeNode.model_validate(data)
    assert again.node_id == "t1"
    assert again.domain == KnowledgeDomain.OWASP_LLM
