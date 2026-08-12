"""Lambda handler for Policy Generator Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "generate_policy",
    "validate_policy_draft",
    "publish_policy",
    "get_policy_draft",
    "list_policy_drafts",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "generate_policy":
            return ok(ag, fn, _generate_policy(params))
        if fn == "validate_policy_draft":
            return ok(ag, fn, _validate_policy_draft(params))
        if fn == "publish_policy":
            return ok(ag, fn, _publish_policy(params))
        if fn == "get_policy_draft":
            return ok(ag, fn, _get_policy_draft(params))
        if fn == "list_policy_drafts":
            return ok(ag, fn, _list_policy_drafts(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _generate_policy(params: dict) -> dict:
    policy_type = params.get("policy_type", "access_control")
    return {"policy_type": policy_type, "draft_id": f"draft-{policy_type[:6]}", "status": "DRAFT", "content": ""}


def _validate_policy_draft(params: dict) -> dict:
    draft_id = params.get("draft_id", "")
    if not draft_id:
        raise ValueError("draft_id is required")
    return {"draft_id": draft_id, "valid": True, "issues": [], "warnings": []}


def _publish_policy(params: dict) -> dict:
    draft_id = params.get("draft_id", "")
    approver = params.get("approver", "")
    if not draft_id:
        raise ValueError("draft_id is required")
    return {"draft_id": draft_id, "policy_id": f"pol-{draft_id[-6:]}", "approver": approver, "status": "PUBLISHED"}


def _get_policy_draft(params: dict) -> dict:
    draft_id = params.get("draft_id", "")
    if not draft_id:
        raise ValueError("draft_id is required")
    return {"draft_id": draft_id, "found": False, "content": ""}


def _list_policy_drafts(params: dict) -> dict:
    policy_type = params.get("policy_type", "")
    status = params.get("status", "DRAFT")
    limit = params.get("limit", 20)
    return {"policy_type": policy_type, "status": status, "drafts": [], "total": 0, "limit": limit}
