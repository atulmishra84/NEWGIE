"""Hybrid semantic + keyword + graph explainable retrieval."""

from __future__ import annotations

import time
from typing import Any

from gie_contracts.knowledge import (
    Confidence,
    ExplainableRetrievalResult,
    KnowledgeQueryRequest,
    RetrievalHit,
)
from gie_observability.logging import get_logger

from knowledge_intelligence.domain.ports import (
    EmbeddingService,
    GraphRepository,
    KnowledgeNodeRepository,
    VectorStore,
    CacheStore,
)
from gie_llm import BedrockLLMClient
from knowledge_intelligence.domain.llm_enhancer import enhance_query_result
from knowledge_intelligence.domain.reasoning import build_reasoning_path
from knowledge_intelligence.settings import Settings

logger = get_logger(__name__)


class HybridQueryEngine:
    def __init__(
        self,
        *,
        nodes: KnowledgeNodeRepository,
        vectors: VectorStore,
        embeddings: EmbeddingService,
        graph: GraphRepository,
        cache: CacheStore,
        settings: Settings,
    ) -> None:
        self._nodes = nodes
        self._vectors = vectors
        self._embeddings = embeddings
        self._graph = graph
        self._cache = cache
        self._settings = settings
        self._llm = (
            BedrockLLMClient(
                region=settings.aws_region,
                model_id=settings.bedrock_model_id,
                max_tokens=settings.bedrock_max_tokens,
                temperature=settings.bedrock_temperature,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                aws_session_token=settings.aws_session_token,
            )
            if settings.bedrock_enabled
            else None
        )

    async def query(
        self,
        request: KnowledgeQueryRequest,
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> ExplainableRetrievalResult:
        started = time.perf_counter()
        cache_key = f"kie:q:{tenant_id}:{hash((request.query, tuple(request.domains), request.top_k, request.version))}"
        cached = await self._cache.get_json(cache_key)
        if cached:
            return ExplainableRetrievalResult.model_validate(cached)

        vectors = await self._embeddings.embed([request.query])
        query_vec = vectors[0]
        filters: dict[str, Any] = {}
        if request.domains:
            filters["domain"] = [d.value for d in request.domains]
        if request.kinds:
            filters["kind"] = [k.value for k in request.kinds]
        if request.version:
            filters["version"] = request.version

        semantic_raw = await self._vectors.search(
            query_vec, top_k=request.top_k * 2, filters=filters or None
        )
        semantic_hits: list[RetrievalHit] = []
        for i, item in enumerate(semantic_raw):
            node = await self._nodes.get_node(item["id"], version=request.version)
            if not node or not node.active:
                continue
            if node.confidence.score < request.min_confidence:
                continue
            semantic_hits.append(
                RetrievalHit(
                    node=node,
                    score=float(item.get("score", 0.0)),
                    rank=i + 1,
                    match_type="semantic",
                    evidence=node.evidence if request.include_evidence else [],
                )
            )

        keyword_hits = await self._keyword_search(request)
        merged = self._merge_hybrid(semantic_hits, keyword_hits, request.top_k)

        graph_paths: list[list[str]] = []
        expanded_ids: list[str] = []
        if (
            request.include_graph
            and self._settings.flag_enable_graph_expansion
            and merged
        ):
            seed_ids = [h.node.node_id for h in merged[:3]]
            expanded_ids, _ = await self._graph.expand(seed_ids, hops=1)
            if len(merged) >= 2:
                paths = await self._graph.shortest_paths(
                    merged[0].node.node_id, merged[1].node.node_id
                )
                graph_paths = paths

        reasoning = build_reasoning_path(
            query=request.query,
            semantic_hits=semantic_hits,
            keyword_hits=keyword_hits,
            graph_expanded=expanded_ids,
        )
        top_conf = merged[0].score if merged else 0.0
        result = ExplainableRetrievalResult(
            query=request.query,
            hits=merged,
            reasoning_path=reasoning,
            confidence=Confidence(
                score=min(1.0, top_conf), rationale="hybrid top-hit score"
            ),
            graph_paths=graph_paths,
            version_pin=request.version,
            took_ms=(time.perf_counter() - started) * 1000,
            agent_version=self._settings.agent_version,
        )
        if self._llm:
            result_dict = result.model_dump(mode="json")
            enhanced = await enhance_query_result(
                result_dict, client=self._llm, original_query=request.query
            )
            result = result.model_copy(
                update={
                    "llm_enhancement": {
                        "narrative": enhanced.get("llm_narrative", ""),
                        "key_insights": enhanced.get("llm_key_insights", []),
                        "recommendations": enhanced.get("llm_recommendations", []),
                        "model": enhanced.get("llm_model", ""),
                    }
                }
            )
        await self._cache.set_json(
            cache_key, result.model_dump(mode="json"), self._settings.cache_ttl_seconds
        )
        logger.info(
            "knowledge_query_completed",
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            hits=len(merged),
            took_ms=result.took_ms,
        )
        return result

    async def _keyword_search(
        self, request: KnowledgeQueryRequest
    ) -> list[RetrievalHit]:
        tokens = [t.lower() for t in request.query.split() if len(t) > 2]
        if not tokens:
            return []
        candidates = await self._nodes.list_nodes(
            domain=request.domains[0].value if request.domains else None,
            version=request.version,
            limit=200,
        )
        scored: list[RetrievalHit] = []
        for node in candidates:
            hay = (
                f"{node.title} {node.summary} {node.body} {' '.join(node.tags)}".lower()
            )
            hits = sum(1 for t in tokens if t in hay)
            if hits == 0:
                continue
            score = hits / len(tokens)
            if score < request.min_confidence and request.min_confidence > 0:
                continue
            scored.append(
                RetrievalHit(
                    node=node,
                    score=score,
                    rank=0,
                    match_type="keyword",
                    evidence=node.evidence if request.include_evidence else [],
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        for i, h in enumerate(scored[: request.top_k * 2]):
            h.rank = i + 1
        return scored[: request.top_k * 2]

    def _merge_hybrid(
        self,
        semantic: list[RetrievalHit],
        keyword: list[RetrievalHit],
        top_k: int,
    ) -> list[RetrievalHit]:
        by_id: dict[str, RetrievalHit] = {}
        for h in semantic:
            by_id[h.node.node_id] = RetrievalHit(
                node=h.node,
                score=h.score * 0.7,
                rank=0,
                match_type="hybrid",
                evidence=h.evidence,
            )
        for h in keyword:
            if h.node.node_id in by_id:
                existing = by_id[h.node.node_id]
                by_id[h.node.node_id] = RetrievalHit(
                    node=h.node,
                    score=min(1.0, existing.score + h.score * 0.3),
                    rank=0,
                    match_type="hybrid",
                    evidence=h.evidence or existing.evidence,
                )
            else:
                by_id[h.node.node_id] = RetrievalHit(
                    node=h.node,
                    score=h.score * 0.5,
                    rank=0,
                    match_type="hybrid",
                    evidence=h.evidence,
                )
        ordered = sorted(by_id.values(), key=lambda x: x.score, reverse=True)[:top_k]
        for i, h in enumerate(ordered):
            h.rank = i + 1
        return ordered
