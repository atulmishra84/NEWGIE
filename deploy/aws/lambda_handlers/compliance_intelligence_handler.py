"""Lambda handler for Compliance Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "analyze_compliance",
    "validate_compliance",
    "get_compliance_report",
    "list_compliance_rules",
    "flag_compliance_violation",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "analyze_compliance":
            return ok(ag, fn, _analyze_compliance(params))
        if fn == "validate_compliance":
            return ok(ag, fn, _validate_compliance(params))
        if fn == "get_compliance_report":
            return ok(ag, fn, _get_compliance_report(params))
        if fn == "list_compliance_rules":
            return ok(ag, fn, _list_compliance_rules(params))
        if fn == "flag_compliance_violation":
            return ok(ag, fn, _flag_violation(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _analyze_compliance(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    framework = params.get("framework", "SOC2")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "framework": framework, "status": "COMPLIANT", "violations": []}


def _validate_compliance(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    rule_id = params.get("rule_id", "")
    if not entity_id or not rule_id:
        raise ValueError("entity_id and rule_id are required")
    return {"entity_id": entity_id, "rule_id": rule_id, "valid": True, "message": "Compliant"}


def _get_compliance_report(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "report_id": f"cmp-{entity_id[:8]}", "score": 100, "violations": []}


def _list_compliance_rules(params: dict) -> dict:
    framework = params.get("framework", "")
    return {"framework": framework, "rules": [], "total": 0}


def _flag_violation(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    rule_id = params.get("rule_id", "")
    severity = params.get("severity", "MEDIUM")
    if not entity_id or not rule_id:
        raise ValueError("entity_id and rule_id are required")
    return {"entity_id": entity_id, "rule_id": rule_id, "severity": severity, "flagged": True, "violation_id": f"vio-{entity_id[:6]}"}
