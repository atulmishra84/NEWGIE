"""Lambda handler for Risk Assessment Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "assess_risk",
    "get_assessment_report",
    "compare_assessments",
    "schedule_assessment",
    "list_assessments",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "assess_risk":
            return ok(ag, fn, _assess_risk(params))
        if fn == "get_assessment_report":
            return ok(ag, fn, _get_assessment_report(params))
        if fn == "compare_assessments":
            return ok(ag, fn, _compare_assessments(params))
        if fn == "schedule_assessment":
            return ok(ag, fn, _schedule_assessment(params))
        if fn == "list_assessments":
            return ok(ag, fn, _list_assessments(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _assess_risk(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    assessment_type = params.get("assessment_type", "comprehensive")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "assessment_type": assessment_type, "assessment_id": f"asmnt-{entity_id[:6]}", "overall_risk": "LOW", "score": 0.1}


def _get_assessment_report(params: dict) -> dict:
    assessment_id = params.get("assessment_id", "")
    if not assessment_id:
        raise ValueError("assessment_id is required")
    return {"assessment_id": assessment_id, "status": "COMPLETED", "risk_areas": [], "mitigation_actions": []}


def _compare_assessments(params: dict) -> dict:
    assessment_id_a = params.get("assessment_id_a", "")
    assessment_id_b = params.get("assessment_id_b", "")
    if not assessment_id_a or not assessment_id_b:
        raise ValueError("assessment_id_a and assessment_id_b are required")
    return {"assessment_id_a": assessment_id_a, "assessment_id_b": assessment_id_b, "delta_score": 0.0, "changes": []}


def _schedule_assessment(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    schedule = params.get("schedule", "weekly")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "schedule": schedule, "next_run": "", "scheduled": True}


def _list_assessments(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    limit = params.get("limit", 20)
    return {"entity_id": entity_id, "assessments": [], "total": 0, "limit": limit}
