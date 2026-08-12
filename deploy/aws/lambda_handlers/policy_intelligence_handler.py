"""Lambda handler for Policy Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "evaluate_policy",
    "list_applicable_policies",
    "get_policy_decision",
    "audit_policy_access",
    "refresh_policy_cache",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "evaluate_policy":
            return ok(ag, fn, _evaluate_policy(params))
        if fn == "list_applicable_policies":
            return ok(ag, fn, _list_applicable_policies(params))
        if fn == "get_policy_decision":
            return ok(ag, fn, _get_policy_decision(params))
        if fn == "audit_policy_access":
            return ok(ag, fn, _audit_policy_access(params))
        if fn == "refresh_policy_cache":
            return ok(ag, fn, _refresh_policy_cache(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _evaluate_policy(params: dict) -> dict:
    subject = params.get("subject", "")
    resource = params.get("resource", "")
    action = params.get("action", "")
    if not subject or not resource:
        raise ValueError("subject and resource are required")
    return {"subject": subject, "resource": resource, "action": action, "decision": "ALLOW", "reasons": []}


def _list_applicable_policies(params: dict) -> dict:
    resource = params.get("resource", "")
    role = params.get("role", "")
    return {"resource": resource, "role": role, "policies": [], "total": 0}


def _get_policy_decision(params: dict) -> dict:
    decision_id = params.get("decision_id", "")
    if not decision_id:
        raise ValueError("decision_id is required")
    return {"decision_id": decision_id, "outcome": "ALLOW", "policy_ids": []}


def _audit_policy_access(params: dict) -> dict:
    subject = params.get("subject", "")
    since = params.get("since", "")
    return {"subject": subject, "since": since, "events": [], "total": 0}


def _refresh_policy_cache(params: dict) -> dict:
    scope = params.get("scope", "all")
    return {"scope": scope, "refreshed": True, "entries_cleared": 0}
