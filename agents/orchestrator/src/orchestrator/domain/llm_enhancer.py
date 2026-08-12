"""Bedrock LLM enhancement for Orchestrator analysis outputs."""

from __future__ import annotations

import logging
from typing import Any

from gie_llm import BedrockLLMClient

logger = logging.getLogger(__name__)


async def enhance_analysis_result(
    trace_dict: dict[str, Any],
    *,
    client: BedrockLLMClient,
) -> dict[str, Any]:
    enhancement = await client.enhance(
        agent_name="GIE Orchestrator",
        deterministic_output={
            "status": trace_dict.get("status"),
            "steps_completed": len(
                [
                    s
                    for s in (trace_dict.get("steps") or [])
                    if s.get("status") == "completed"
                ]
            ),
            "steps_failed": len(
                [
                    s
                    for s in (trace_dict.get("steps") or [])
                    if s.get("status") == "failed"
                ]
            ),
            "overall_risk": trace_dict.get("risk_score"),
            "policy_decision": trace_dict.get("policy_decision"),
        },
        context_summary=(
            "Summarize the full GIE multi-agent pipeline execution. "
            "Explain the overall AI application security posture and next steps."
        ),
    )
    if enhancement.get("narrative"):
        trace_dict["llm_narrative"] = enhancement["narrative"]
        trace_dict["llm_key_insights"] = enhancement.get("key_insights", [])
        trace_dict["llm_recommendations"] = enhancement.get("recommendations", [])
        trace_dict["llm_model"] = client._model_id
    return trace_dict
