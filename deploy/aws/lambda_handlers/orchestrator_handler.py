"""Lambda handler for Orchestrator Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "start_workflow",
    "get_workflow_status",
    "cancel_workflow",
    "analyze_workflow",
    "list_workflows",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "start_workflow":
            return ok(ag, fn, _start_workflow(params))
        if fn == "get_workflow_status":
            return ok(ag, fn, _get_workflow_status(params))
        if fn == "cancel_workflow":
            return ok(ag, fn, _cancel_workflow(params))
        if fn == "analyze_workflow":
            return ok(ag, fn, _analyze_workflow(params))
        if fn == "list_workflows":
            return ok(ag, fn, _list_workflows(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _start_workflow(params: dict) -> dict:
    workflow_type = params.get("workflow_type", "")
    entity_id = params.get("entity_id", "")
    if not workflow_type or not entity_id:
        raise ValueError("workflow_type and entity_id are required")
    return {"workflow_type": workflow_type, "entity_id": entity_id, "workflow_id": f"wf-{entity_id[:6]}", "status": "RUNNING"}


def _get_workflow_status(params: dict) -> dict:
    workflow_id = params.get("workflow_id", "")
    if not workflow_id:
        raise ValueError("workflow_id is required")
    return {"workflow_id": workflow_id, "status": "COMPLETED", "steps_completed": 0, "steps_total": 0}


def _cancel_workflow(params: dict) -> dict:
    workflow_id = params.get("workflow_id", "")
    reason = params.get("reason", "")
    if not workflow_id:
        raise ValueError("workflow_id is required")
    return {"workflow_id": workflow_id, "reason": reason, "cancelled": True}


def _analyze_workflow(params: dict) -> dict:
    workflow_id = params.get("workflow_id", "")
    if not workflow_id:
        raise ValueError("workflow_id is required")
    return {"workflow_id": workflow_id, "analysis": {}, "bottlenecks": [], "recommendations": []}


def _list_workflows(params: dict) -> dict:
    status = params.get("status", "")
    limit = params.get("limit", 20)
    return {"status": status, "workflows": [], "total": 0, "limit": limit}
