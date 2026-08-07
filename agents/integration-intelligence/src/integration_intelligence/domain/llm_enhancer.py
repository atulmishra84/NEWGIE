"""Bedrock LLM enhancement for Integration Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import BedrockLLMClient

logger = logging.getLogger(__name__)


async def enhance_integration_report(
    report_dict: dict[str, Any],
    *,
    client: BedrockLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Integration Intelligence",
        deterministic_output={
            "platforms_connected": report_dict.get("platforms_connected"),
            "health_summary": report_dict.get("health_summary"),
            "circuit_breakers": report_dict.get("circuit_breakers"),
        },
        context_summary=(
            "Evaluate enterprise platform integrations for AI guardrails. "
            "Summarize connection health and recommend resilience improvements."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
