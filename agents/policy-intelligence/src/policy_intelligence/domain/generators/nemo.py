from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle

def render(recs: list[GuardrailRecommendation], bundle: PolicyInputBundle) -> dict[str, Any]:
    colang = """define user ask general
  ".*"

define base flow
  user ask general
  bot respond safely

define bot respond safely
  "I will follow organizational safety policies."

define flow jailbreak attempt
  user ask general
  bot refuse jailbreak

define bot refuse jailbreak
  "I cannot bypass safety policies."
"""
    return {
        "vendor": "nvidia_nemo",
        "version": "1.0",
        "controls": [{"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls],
        "nemo_guardrails": {
            "rails": {
                "input": {"flows": ["jailbreak attempt", "self check input"]},
                "output": {"flows": ["self check output"]},
                "dialog": {"single_call": {"enabled": True}},
            },
            "models": [{"type": "main", "engine": "openai", "model": "gpt-4o-mini"}],
        },
        "colang": colang,
        "rationale": [r.why[0] for r in recs if r.why],
    }
