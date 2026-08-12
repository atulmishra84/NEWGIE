"""Bedrock LLM enhancement for Recommendation Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import AnthropicLLMClient

logger = logging.getLogger(__name__)


async def enhance_recommendation_report(
    report_dict: dict[str, Any],
    *,
    client: AnthropicLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Recommendation Intelligence",
        deterministic_output={
            "total_count": report_dict.get("total_count"),
            "critical_count": report_dict.get("critical_count"),
            "items": [
                {
                    k: v
                    for k, v in item.items()
                    if k in ("id", "title", "priority", "category", "effort")
                }
                for item in (report_dict.get("items") or [])[:8]
            ],
        },
        context_summary=(
            "Prioritize and contextualize security recommendations for an AI application. "
            "Explain the business impact and suggest a sequenced implementation roadmap."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
