"""Lambda handler for Learning Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "submit_feedback",
    "trigger_learning",
    "approve_learning_update",
    "get_learning_status",
    "list_feedback_events",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "submit_feedback":
            return ok(ag, fn, _submit_feedback(params))
        if fn == "trigger_learning":
            return ok(ag, fn, _trigger_learning(params))
        if fn == "approve_learning_update":
            return ok(ag, fn, _approve_learning_update(params))
        if fn == "get_learning_status":
            return ok(ag, fn, _get_learning_status(params))
        if fn == "list_feedback_events":
            return ok(ag, fn, _list_feedback_events(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _submit_feedback(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    feedback_type = params.get("feedback_type", "correction")
    payload = params.get("payload", "")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "feedback_type": feedback_type, "feedback_id": f"fb-{entity_id[:6]}", "accepted": True}


def _trigger_learning(params: dict) -> dict:
    model_id = params.get("model_id", "default")
    scope = params.get("scope", "incremental")
    return {"model_id": model_id, "scope": scope, "job_id": f"learn-{model_id[:8]}", "status": "QUEUED"}


def _approve_learning_update(params: dict) -> dict:
    update_id = params.get("update_id", "")
    approver = params.get("approver", "")
    if not update_id:
        raise ValueError("update_id is required")
    return {"update_id": update_id, "approver": approver, "status": "APPROVED"}


def _get_learning_status(params: dict) -> dict:
    job_id = params.get("job_id", "")
    if not job_id:
        raise ValueError("job_id is required")
    return {"job_id": job_id, "status": "COMPLETED", "accuracy_delta": 0.0}


def _list_feedback_events(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    limit = params.get("limit", 20)
    return {"entity_id": entity_id, "events": [], "total": 0, "limit": limit}
