"""Lambda handler for Policy Engine Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "execute_policy",
    "register_policy",
    "deactivate_policy",
    "test_policy",
    "list_active_policies",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "execute_policy":
            return ok(ag, fn, _execute_policy(params))
        if fn == "register_policy":
            return ok(ag, fn, _register_policy(params))
        if fn == "deactivate_policy":
            return ok(ag, fn, _deactivate_policy(params))
        if fn == "test_policy":
            return ok(ag, fn, _test_policy(params))
        if fn == "list_active_policies":
            return ok(ag, fn, _list_active_policies(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _execute_policy(params: dict) -> dict:
    policy_id = params.get("policy_id", "")
    subject = params.get("subject", "")
    resource = params.get("resource", "")
    if not policy_id or not subject:
        raise ValueError("policy_id and subject are required")
    return {"policy_id": policy_id, "subject": subject, "resource": resource, "result": "ALLOW", "execution_ms": 0}


def _register_policy(params: dict) -> dict:
    policy_name = params.get("policy_name", "")
    policy_content = params.get("policy_content", "")
    policy_type = params.get("policy_type", "ABAC")
    if not policy_name or not policy_content:
        raise ValueError("policy_name and policy_content are required")
    return {"policy_name": policy_name, "policy_type": policy_type, "policy_id": f"pol-{policy_name[:8]}", "status": "ACTIVE"}


def _deactivate_policy(params: dict) -> dict:
    policy_id = params.get("policy_id", "")
    if not policy_id:
        raise ValueError("policy_id is required")
    return {"policy_id": policy_id, "deactivated": True}


def _test_policy(params: dict) -> dict:
    policy_id = params.get("policy_id", "")
    test_case = params.get("test_case", "")
    if not policy_id or not test_case:
        raise ValueError("policy_id and test_case are required")
    return {"policy_id": policy_id, "test_case": test_case, "passed": True, "result": "ALLOW"}


def _list_active_policies(params: dict) -> dict:
    policy_type = params.get("policy_type", "")
    limit = params.get("limit", 20)
    return {"policy_type": policy_type, "policies": [], "total": 0, "limit": limit}
