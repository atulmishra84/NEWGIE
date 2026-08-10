"""Bedrock LLM enhancement for Learning Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import BedrockLLMClient

logger = logging.getLogger(__name__)


async def enhance_learning_report(
    report_dict: dict[str, Any],
    *,
    client: BedrockLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Learning Intelligence",
        deterministic_output={
            "drift_findings": (report_dict.get("drift_findings") or [])[:8],
            "improved_recommendations": len(
                report_dict.get("improved_recommendations") or []
            ),
            "knowledge_changes": len(report_dict.get("knowledge_changes") or []),
        },
        context_summary=(
            "Analyze feedback-driven learning cycles for AI guardrails. "
            "Identify drift patterns, explain model improvements, and propose knowledge updates."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
