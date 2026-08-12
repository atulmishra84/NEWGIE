from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle


def render(
    recs: list[GuardrailRecommendation], bundle: PolicyInputBundle
) -> dict[str, Any]:
    return {
        "vendor": "autogen",
        "version": "1.0",
        "controls": [
            {"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls
        ],
        "autogen": {
            "code_execution_config": {"use_docker": True, "timeout": 60}
            if any(r.guardrail_id == "gr-tool-allowlist" for r in recs)
            else False,
            "human_input_mode": "ALWAYS"
            if any(r.priority.value == "P0" for r in recs)
            else "TERMINATE",
            "max_consecutive_auto_reply": 3,
            "function_map_allowlist": True,
            "safety": {"block_shell": True, "output_filter": True},
        },
        "rationale": [r.why[0] for r in recs if r.why],
    }
