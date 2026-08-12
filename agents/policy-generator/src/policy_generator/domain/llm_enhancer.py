"""Bedrock LLM enhancement for Policy Generator outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import AnthropicLLMClient

logger = logging.getLogger(__name__)


async def enhance_policy_package(
    package_dict: dict[str, Any],
    *,
    client: AnthropicLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="Policy Generator",
        deterministic_output={
            "package_id": package_dict.get("package_id"),
            "policy_count": len(package_dict.get("artifacts") or {}),
            "formats": list((package_dict.get("artifacts") or {}).keys()),
            "validation_status": package_dict.get("validation", {}).get("status"),
        },
        context_summary=(
            "Summarize generated deployment-ready AI guardrail policies. "
            "Explain what each format is used for and how to deploy them."
        ),
    )
    if enhancement.get("narrative"):
        package_dict["llm_narrative"] = enhancement["narrative"]
        package_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        package_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        package_dict["llm_model"] = client._model_id
    return package_dict
