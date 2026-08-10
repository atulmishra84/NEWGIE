from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle


def render(
    recs: list[GuardrailRecommendation], bundle: PolicyInputBundle
) -> dict[str, Any]:
    return {
        "vendor": "crewai",
        "version": "1.0",
        "controls": [
            {"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls
        ],
        "crewai": {
            "process": "hierarchical"
            if any(r.guardrail_id == "gr-identity-rbac" for r in recs)
            else "sequential",
            "manager_llm_guards": {"max_iter": 5, "allow_delegation": False},
            "agent_defaults": {
                "allow_code_execution": False,
                "respect_context_window": True,
                "tools_filter": "allowlist",
            },
            "task_guards": {
                "output_pydantic_validation": True,
                "max_execution_time": 120,
            },
        },
        "rationale": [r.why[0] for r in recs if r.why],
    }
