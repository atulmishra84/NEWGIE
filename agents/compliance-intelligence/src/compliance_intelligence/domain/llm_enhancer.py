"""Bedrock LLM enhancement for Compliance Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import AnthropicLLMClient

logger = logging.getLogger(__name__)


async def enhance_compliance_report(
    report_dict: dict[str, Any],
    *,
    client: AnthropicLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Compliance Intelligence",
        deterministic_output={
            "overall_score": report_dict.get("overall_score"),
            "applicable_frameworks": (report_dict.get("applicable_frameworks") or [])[
                :8
            ],
            "gaps": (report_dict.get("gaps") or [])[:10],
            "audit_package_summary": report_dict.get("audit_package", {}).get(
                "summary"
            ),
        },
        context_summary=(
            "Summarize regulatory compliance posture, identify the highest-severity gaps, "
            "and recommend prioritized remediation steps."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
