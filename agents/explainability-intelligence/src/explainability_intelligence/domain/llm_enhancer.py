"""Bedrock LLM enhancement for Explainability Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import BedrockLLMClient

logger = logging.getLogger(__name__)


async def enhance_explanation_report(
    report_dict: dict[str, Any],
    *,
    client: BedrockLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Explainability Intelligence",
        deterministic_output={
            "audience_explanations": [
                {"audience": e.get("audience"), "summary": e.get("summary")}
                for e in (report_dict.get("audience_explanations") or [])[:6]
            ],
            "decision_title": report_dict.get("decision_title"),
            "overall_confidence": report_dict.get("overall_confidence"),
        },
        context_summary=(
            "Enhance multi-audience explanations of AI guardrail decisions. "
            "Ensure clarity for executives, engineers, and compliance officers."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
