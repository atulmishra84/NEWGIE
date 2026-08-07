"""Bedrock LLM enhancement for Policy Intelligence outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import BedrockLLMClient

logger = logging.getLogger(__name__)


async def enhance_policy_report(
    report_dict: dict[str, Any],
    *,
    client: BedrockLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Policy Intelligence",
        deterministic_output={
            "selected_guardrails": (report_dict.get("selected_guardrails") or [])[:10],
            "policy_score": report_dict.get("policy_score"),
            "deployment_artifacts": list((report_dict.get("deployment_artifacts") or {}).keys()),
        },
        context_summary=(
            "Explain the selected guardrails, why they address identified risks, "
            "and how to deploy them effectively."
        ),
    )
    if enhancement.get("narrative"):
        report_dict["llm_narrative"] = enhancement["narrative"]
        report_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        report_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        report_dict["llm_model"] = client._model_id
    return report_dict
