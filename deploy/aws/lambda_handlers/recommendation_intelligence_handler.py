"""Lambda handler for Recommendation Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "generate_recommendations",
    "approve_recommendation",
    "reject_recommendation",
    "get_recommendation",
    "list_recommendations",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "generate_recommendations":
            return ok(ag, fn, _generate_recommendations(params))
        if fn == "approve_recommendation":
            return ok(ag, fn, _approve_recommendation(params))
        if fn == "reject_recommendation":
            return ok(ag, fn, _reject_recommendation(params))
        if fn == "get_recommendation":
            return ok(ag, fn, _get_recommendation(params))
        if fn == "list_recommendations":
            return ok(ag, fn, _list_recommendations(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _generate_recommendations(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    context_type = params.get("context_type", "general")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "context_type": context_type, "recommendations": [], "total": 0}


def _approve_recommendation(params: dict) -> dict:
    rec_id = params.get("recommendation_id", "")
    reviewer = params.get("reviewer", "")
    if not rec_id:
        raise ValueError("recommendation_id is required")
    return {"recommendation_id": rec_id, "reviewer": reviewer, "status": "APPROVED"}


def _reject_recommendation(params: dict) -> dict:
    rec_id = params.get("recommendation_id", "")
    reason = params.get("reason", "")
    if not rec_id:
        raise ValueError("recommendation_id is required")
    return {"recommendation_id": rec_id, "reason": reason, "status": "REJECTED"}


def _get_recommendation(params: dict) -> dict:
    rec_id = params.get("recommendation_id", "")
    if not rec_id:
        raise ValueError("recommendation_id is required")
    return {"recommendation_id": rec_id, "found": False}


def _list_recommendations(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    status = params.get("status", "PENDING")
    limit = params.get("limit", 20)
    return {"entity_id": entity_id, "status": status, "recommendations": [], "total": 0, "limit": limit}
