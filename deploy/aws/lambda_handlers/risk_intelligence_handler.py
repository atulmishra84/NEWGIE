"""Lambda handler for Risk Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "calculate_risk_score",
    "recalculate_risk",
    "get_risk_report",
    "list_risk_factors",
    "set_risk_threshold",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "calculate_risk_score":
            return ok(ag, fn, _calculate_risk_score(params))
        if fn == "recalculate_risk":
            return ok(ag, fn, _recalculate_risk(params))
        if fn == "get_risk_report":
            return ok(ag, fn, _get_risk_report(params))
        if fn == "list_risk_factors":
            return ok(ag, fn, _list_risk_factors(params))
        if fn == "set_risk_threshold":
            return ok(ag, fn, _set_risk_threshold(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _calculate_risk_score(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    risk_type = params.get("risk_type", "operational")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "risk_type": risk_type, "score": 0.0, "level": "LOW"}


def _recalculate_risk(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "recalculated": True, "new_score": 0.0}


def _get_risk_report(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "report_id": f"rpt-{entity_id[:8]}", "factors": [], "summary": "No risks detected"}


def _list_risk_factors(params: dict) -> dict:
    risk_type = params.get("risk_type", "")
    return {"risk_type": risk_type, "factors": [], "total": 0}


def _set_risk_threshold(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    threshold = params.get("threshold", 0.7)
    return {"entity_id": entity_id, "threshold": threshold, "updated": True}
