from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle


def render(
    recs: list[GuardrailRecommendation], bundle: PolicyInputBundle
) -> dict[str, Any]:
    return {
        "vendor": "langgraph",
        "version": "1.0",
        "controls": [
            {"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls
        ],
        "langgraph": {
            "pre_model_hooks": ["prompt_injection_filter", "pii_redact_input"]
            if any(r.guardrail_id == "gr-prompt-injection" for r in recs)
            else [],
            "post_model_hooks": ["output_filter", "secret_scan"]
            if any(r.guardrail_id == "gr-output-filter" for r in recs)
            else [],
            "tool_node": {
                "allowlist": True,
                "denied_tools": ["shell", "python_repl"]
                if any(r.guardrail_id == "gr-tool-allowlist" for r in recs)
                else [],
                "require_human_approval_for": [
                    "write_file",
                    "send_email",
                    "execute_sql",
                ],
            },
            "checkpointer": {"enabled": True, "ttl_seconds": 3600},
        },
        "rationale": [r.why[0] for r in recs if r.why],
    }
