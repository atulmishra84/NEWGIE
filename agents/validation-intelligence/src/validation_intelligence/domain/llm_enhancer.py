"""Bedrock LLM enhancement for Validation Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import AnthropicLLMClient

logger = logging.getLogger(__name__)


async def enhance_validation_report(
    report_dict: dict[str, Any],
    *,
    client: AnthropicLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Validation Intelligence",
        deterministic_output={
            "verdict": report_dict.get("verdict"),
            "approval_status": report_dict.get("approval_status"),
            "findings": [
                {
                    k: v
                    for k, v in f.items()
                    if k in ("check", "category", "verdict", "message")
                }
                for f in (report_dict.get("findings") or [])[:10]
            ],
        },
        context_summary=(
            "Evaluate pre-deployment policy validation results. Explain what passed, "
            "what failed, and what must be fixed before deployment can proceed."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
