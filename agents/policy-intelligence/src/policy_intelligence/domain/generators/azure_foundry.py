from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle

def render(recs: list[GuardrailRecommendation], bundle: PolicyInputBundle) -> dict[str, Any]:
    return {
        "vendor": "azure_ai_foundry",
        "version": "1.0",
        "controls": [{"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls],
        "azure_ai_foundry": {
            "content_safety": {
                "enabled": True,
                "categories": ["Hate", "SelfHarm", "Sexual", "Violence"],
                "prompt_shields": {"jailbreak": True, "indirect_attack": True},
            },
            "entra_id": {"required": True, "managed_identity": True},
            "network": {"private_endpoint": True},
            "grounding": {"on_your_data_strictness": "medium"},
        },
        "rationale": [r.why[0] for r in recs if r.why],
    }
