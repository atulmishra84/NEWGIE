"""Bedrock LLM enhancement for Context Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import BedrockLLMClient

logger = logging.getLogger(__name__)


async def enhance_context_model(
    context_dict: dict[str, Any],
    *,
    client: BedrockLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Context Intelligence",
        deterministic_output={
            "frameworks": context_dict.get("ai", {}).get("frameworks"),
            "models": context_dict.get("ai", {}).get("models"),
            "mcp_servers": context_dict.get("ai", {}).get("mcp_servers"),
            "secrets_found": len(context_dict.get("security", {}).get("secrets") or []),
            "deployment_type": context_dict.get("deployment", {}).get("type"),
        },
        context_summary=(
            "Analyze the discovered AI application context. Highlight key frameworks, "
            "model usage patterns, security concerns, and deployment topology insights."
        ),
    )
    if enhancement.get("narrative"):
        context_dict["llm_narrative"] = enhancement["narrative"]
        context_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        context_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        context_dict["llm_model"] = client._model_id
    return context_dict
