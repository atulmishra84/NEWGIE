"""Lambda handler for Context Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "start_context_scan",
    "get_scan_status",
    "list_context_findings",
    "get_context_model",
    "diff_context_models",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "start_context_scan":
            return ok(ag, fn, _start_context_scan(params))
        if fn == "get_scan_status":
            return ok(ag, fn, _get_scan_status(params))
        if fn == "list_context_findings":
            return ok(ag, fn, _list_context_findings(params))
        if fn == "get_context_model":
            return ok(ag, fn, _get_context_model(params))
        if fn == "diff_context_models":
            return ok(ag, fn, _diff_context_models(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _start_context_scan(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    scan_type = params.get("scan_type", "full")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"scan_id": f"scan-{entity_id[:8]}", "status": "STARTED", "scan_type": scan_type}


def _get_scan_status(params: dict) -> dict:
    scan_id = params.get("scan_id", "")
    if not scan_id:
        raise ValueError("scan_id is required")
    return {"scan_id": scan_id, "status": "COMPLETED", "findings_count": 0}


def _list_context_findings(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    limit = params.get("limit", 20)
    return {"entity_id": entity_id, "findings": [], "total": 0, "limit": limit}


def _get_context_model(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "model_version": "v1", "attributes": {}}


def _diff_context_models(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    from_version = params.get("from_version", "v0")
    to_version = params.get("to_version", "v1")
    return {"entity_id": entity_id, "from_version": from_version, "to_version": to_version, "changes": []}
