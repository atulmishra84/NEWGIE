from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle

def render(recs: list[GuardrailRecommendation], bundle: PolicyInputBundle) -> dict[str, Any]:
    denied_tools = ["shell", "exec", "python_repl"]
    rego = """package gie.policy.opa_runtime

import future.keywords.if
import future.keywords.in

default allow := false

deny[msg] {
  input.tool.name in {"shell", "exec", "python_repl"}
  msg := sprintf("tool %v blocked by GIE policy", [input.tool.name])
}

deny[msg] {
  input.network.egress
  not net.cidr_contains("10.0.0.0/8", input.network.destination)
  not net.cidr_contains("192.168.0.0/16", input.network.destination)
  msg := "egress destination not in allowlist"
}

allow if {
  count(deny) == 0
}
"""
    return {
        "vendor": "opa_rego",
        "version": "1.0",
        "controls": [{"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls],
        "opa": {
            "package": "gie.policy.opa_runtime",
            "denied_tools": denied_tools,
            "require_human_for_p0": True,
        },
        "rego": rego,
        "rationale": [r.why[0] for r in recs if r.why],
    }
