"""Lambda handler for Explainability Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "explain_decision",
    "get_reasoning_trace",
    "explain_risk_score",
    "explain_policy_outcome",
    "list_explanations",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "explain_decision":
            return ok(ag, fn, _explain_decision(params))
        if fn == "get_reasoning_trace":
            return ok(ag, fn, _get_reasoning_trace(params))
        if fn == "explain_risk_score":
            return ok(ag, fn, _explain_risk_score(params))
        if fn == "explain_policy_outcome":
            return ok(ag, fn, _explain_policy_outcome(params))
        if fn == "list_explanations":
            return ok(ag, fn, _list_explanations(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _explain_decision(params: dict) -> dict:
    decision_id = params.get("decision_id", "")
    detail_level = params.get("detail_level", "summary")
    if not decision_id:
        raise ValueError("decision_id is required")
    return {"decision_id": decision_id, "detail_level": detail_level, "explanation": "Decision was made based on available context.", "factors": []}


def _get_reasoning_trace(params: dict) -> dict:
    trace_id = params.get("trace_id", "")
    if not trace_id:
        raise ValueError("trace_id is required")
    return {"trace_id": trace_id, "steps": [], "conclusion": ""}


def _explain_risk_score(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    score = params.get("score", 0.0)
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "score": score, "explanation": "Risk score based on historical data.", "contributing_factors": []}


def _explain_policy_outcome(params: dict) -> dict:
    policy_id = params.get("policy_id", "")
    outcome = params.get("outcome", "ALLOW")
    if not policy_id:
        raise ValueError("policy_id is required")
    return {"policy_id": policy_id, "outcome": outcome, "explanation": "Policy evaluated all applicable rules.", "rules_applied": []}


def _list_explanations(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    limit = params.get("limit", 10)
    return {"entity_id": entity_id, "explanations": [], "total": 0, "limit": limit}
