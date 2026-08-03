"""Explainable retrieval reasoning helpers."""

from __future__ import annotations

from gie_contracts.knowledge import Confidence, ReasoningStep, RetrievalHit


def build_reasoning_path(
    *,
    query: str,
    semantic_hits: list[RetrievalHit],
    keyword_hits: list[RetrievalHit],
    graph_expanded: list[str],
) -> list[ReasoningStep]:
    steps: list[ReasoningStep] = []
    steps.append(
        ReasoningStep(
            step=1,
            action="parse_query",
            detail=f"Normalized query for hybrid retrieval: {query[:200]}",
            confidence=Confidence(score=1.0, rationale="deterministic parse"),
        )
    )
    steps.append(
        ReasoningStep(
            step=2,
            action="semantic_search",
            detail=f"Vector search returned {len(semantic_hits)} candidates",
            node_ids=[h.node.node_id for h in semantic_hits[:5]],
            confidence=Confidence(
                score=semantic_hits[0].score if semantic_hits else 0.0,
                rationale="top semantic similarity",
            ),
        )
    )
    steps.append(
        ReasoningStep(
            step=3,
            action="keyword_search",
            detail=f"Keyword/BM25-style search returned {len(keyword_hits)} candidates",
            node_ids=[h.node.node_id for h in keyword_hits[:5]],
            confidence=Confidence(score=0.8 if keyword_hits else 0.0),
        )
    )
    if graph_expanded:
        steps.append(
            ReasoningStep(
                step=4,
                action="graph_expansion",
                detail=f"Expanded {len(graph_expanded)} related nodes via knowledge graph",
                node_ids=graph_expanded[:10],
                confidence=Confidence(score=0.75, rationale="1-hop neighborhood"),
            )
        )
    steps.append(
        ReasoningStep(
            step=len(steps) + 1,
            action="rerank_and_explain",
            detail="Merged hybrid scores, attached evidence, produced explainable ranking",
            confidence=Confidence(score=0.85),
        )
    )
    return steps
