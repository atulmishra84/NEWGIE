"""Bedrock LLM enhancement for Knowledge Intelligence query results."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import AnthropicLLMClient

logger = logging.getLogger(__name__)


async def enhance_query_result(
    result_dict: dict[str, Any],
    *,
    client: AnthropicLLMClient,
    original_query: str = "",
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Knowledge Intelligence",
        deterministic_output={
            "query": original_query[:200],
            "hits": [
                {
                    k: v
                    for k, v in h.items()
                    if k in ("node_id", "title", "score", "domain")
                }
                for h in (result_dict.get("hits") or [])[:8]
            ],
            "explanation": result_dict.get("explanation"),
        },
        context_summary=(
            "Synthesize knowledge graph retrieval results about AI security, compliance, and guardrails. "
            "Explain how retrieved nodes answer the query and highlight actionable guidance."
        ),
    )
    if enhancement.get("narrative"):
        result_dict["llm_narrative"] = enhancement["narrative"]
        result_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        result_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        result_dict["llm_model"] = client._model_id
    return result_dict
