"""Bedrock LLM enhancement for Risk Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import AnthropicLLMClient

logger = logging.getLogger(__name__)


async def enhance_risk_report(
    report_dict: dict[str, Any],
    *,
    client: AnthropicLLMClient,
) -> dict[str, Any]:
    """Enrich a deterministic risk report with LLM narrative and insights."""
    enhancement = await client.enhance(
        agent_name="Risk Intelligence",
        deterministic_output={
            "overall_score": report_dict.get("overall_score"),
            "trust_score": report_dict.get("trust_score"),
            "severity": report_dict.get("severity"),
            "factors": (report_dict.get("factors") or [])[:10],
            "heatmap": (report_dict.get("heatmap") or [])[:5],
        },
        context_summary=(
            "Assess AI application risk posture. Highlight the most critical risk categories, "
            "their business impact, and the top 3 immediate remediation actions."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
