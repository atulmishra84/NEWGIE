from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle


def render(
    recs: list[GuardrailRecommendation], bundle: PolicyInputBundle
) -> dict[str, Any]:
    moderation = any(
        r.guardrail_id in {"gr-topic-safety", "gr-output-filter"} for r in recs
    )
    return {
        "vendor": "openai",
        "version": "1.0",
        "controls": [
            {"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls
        ],
        "openai": {
            "moderation": {"enabled": moderation, "models": ["omni-moderation-latest"]},
            "responses_api": {
                "instructions_priority": "system_over_user",
                "tool_choice": "required"
                if any(r.guardrail_id == "gr-tool-allowlist" for r in recs)
                else "auto",
            },
            "allowed_tools": _tools(bundle),
            "rate_limits": {"rpm": 60, "tpm": 100000}
            if any(r.guardrail_id == "gr-rate-limit" for r in recs)
            else {},
            "data_controls": {
                "store": False,
                "pii_filtering": any(r.guardrail_id == "gr-pii-presidio" for r in recs),
            },
        },
        "rationale": [r.why[0] for r in recs if r.why],
    }


def _tools(bundle: PolicyInputBundle) -> list[str]:
    tools = (
        bundle.context.get("interfaces", {}).get("tools")
        or bundle.context.get("tools")
        or []
    )
    names = []
    for t in tools:
        if isinstance(t, dict):
            names.append(t.get("name", "tool"))
        else:
            names.append(str(t))
    return names or ["search", "retrieve"]
