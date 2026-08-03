from gie_contracts.knowledge import Confidence, KnowledgeDomain, KnowledgeNode, NodeKind, RetrievalHit
from knowledge_intelligence.domain.reasoning import build_reasoning_path


def test_reasoning_path_steps():
    node = KnowledgeNode(
        node_id="n1",
        kind=NodeKind.THREAT,
        domain=KnowledgeDomain.OWASP_LLM,
        title="X",
        confidence=Confidence(score=0.8),
    )
    hit = RetrievalHit(node=node, score=0.8, rank=1, match_type="semantic")
    steps = build_reasoning_path(query="injection", semantic_hits=[hit], keyword_hits=[], graph_expanded=["n2"])
    assert len(steps) >= 4
    assert steps[0].action == "parse_query"
