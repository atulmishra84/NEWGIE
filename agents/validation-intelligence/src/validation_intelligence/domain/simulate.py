"""Simulate policy execution against scenarios."""

from __future__ import annotations

from typing import Any

from gie_contracts.validation import SimulationReport, SimulationStep


DEFAULT_SCENARIOS = [
    {
        "name": "benign_user_query",
        "actions": [
            {
                "action": "invoke",
                "prompt_injection_score": 0.1,
                "contains_pii": False,
                "tool_name": None,
            },
        ],
        "expect_allow": True,
    },
    {
        "name": "prompt_injection_attempt",
        "actions": [
            {
                "action": "invoke",
                "prompt_injection_score": 0.95,
                "contains_pii": False,
                "tool_name": None,
            },
        ],
        "expect_allow": False,
    },
    {
        "name": "pii_egress",
        "actions": [
            {
                "action": "invoke",
                "prompt_injection_score": 0.1,
                "contains_pii": True,
                "tool_name": None,
            },
        ],
        "expect_allow": False,
    },
    {
        "name": "dangerous_tool_without_approval",
        "actions": [
            {
                "action": "invoke",
                "prompt_injection_score": 0.1,
                "contains_pii": False,
                "tool_name": "shell",
                "requires_approval": True,
                "human_approved": False,
            },
        ],
        "expect_allow": False,
    },
]


def _policy_rules(docs: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "block_prompt_injection": True,
        "redact_pii": True,
        "tool_allowlist": True,
        "require_human_approval": True,
        "allowed_tools": ["search"],
    }
    for d in docs:
        body = d.get("body") or {}
        rules = (
            body.get("rules")
            or (body.get("spec") or {}).get("rules")
            or body.get("settings")
            or {}
        )
        if isinstance(rules, dict):
            merged.update(
                {
                    k: v
                    for k, v in rules.items()
                    if isinstance(v, (bool, str, int, float, list))
                }
            )
        # openai steps imply filters
        for step in body.get("steps") or []:
            if isinstance(step, dict) and step.get("type") == "input_filters":
                if "jailbreak" in (step.get("filters") or []):
                    merged["block_prompt_injection"] = True
            if isinstance(step, dict) and step.get("type") == "tool_restrictions":
                merged["tool_allowlist"] = step.get("mode") == "allowlist"
    return merged


def _decide(action: dict[str, Any], rules: dict[str, Any]) -> tuple[bool, str]:
    if (
        rules.get("block_prompt_injection")
        and float(action.get("prompt_injection_score") or 0) > 0.7
    ):
        return False, "denied: prompt_injection"
    if rules.get("redact_pii") and action.get("contains_pii"):
        return False, "denied: pii"
    tool = action.get("tool_name")
    if tool and rules.get("tool_allowlist"):
        allowed = set(rules.get("allowed_tools") or ["search"])
        if tool not in allowed:
            return False, f"denied: tool {tool} not allowlisted"
    if (
        rules.get("require_human_approval")
        and action.get("requires_approval")
        and not action.get("human_approved")
    ):
        return False, "denied: human_approval_required"
    return True, "allowed"


def run_simulations(
    docs: list[dict[str, Any]],
    scenarios: list[dict[str, Any]] | None = None,
    runtime: dict[str, Any] | None = None,
) -> list[SimulationReport]:
    rules = _policy_rules(docs)
    if runtime and runtime.get("allowed_tools"):
        rules["allowed_tools"] = list(runtime["allowed_tools"])
    scen_list = scenarios or DEFAULT_SCENARIOS
    reports: list[SimulationReport] = []
    for scen in scen_list:
        steps: list[SimulationStep] = []
        ok = True
        for i, action in enumerate(scen.get("actions") or [], start=1):
            allowed, result = _decide(action, rules)
            expect = scen.get("expect_allow")
            step_ok = allowed if expect is None else (allowed == bool(expect))
            if not step_ok:
                ok = False
            steps.append(
                SimulationStep(
                    step=i,
                    action=str(action.get("action") or "invoke"),
                    input_summary=str({k: action[k] for k in action if k != "action"}),
                    result=result,
                    allowed=allowed,
                    notes=None if step_ok else f"expected_allow={expect}",
                )
            )
        reports.append(
            SimulationReport(
                scenario_name=str(scen.get("name") or "scenario"),
                passed=ok,
                steps=steps,
                summary=("passed" if ok else "failed")
                + f" under rules={list(rules.keys())}",
            )
        )
    return reports
