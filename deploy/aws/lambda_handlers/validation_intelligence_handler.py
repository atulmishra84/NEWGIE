"""Lambda handler for Validation Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "validate_entity",
    "simulate_scenario",
    "get_validation_result",
    "list_validation_rules",
    "run_validation_suite",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "validate_entity":
            return ok(ag, fn, _validate_entity(params))
        if fn == "simulate_scenario":
            return ok(ag, fn, _simulate_scenario(params))
        if fn == "get_validation_result":
            return ok(ag, fn, _get_validation_result(params))
        if fn == "list_validation_rules":
            return ok(ag, fn, _list_validation_rules(params))
        if fn == "run_validation_suite":
            return ok(ag, fn, _run_validation_suite(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _validate_entity(params: dict) -> dict:
    entity_id = params.get("entity_id", "")
    schema_id = params.get("schema_id", "default")
    if not entity_id:
        raise ValueError("entity_id is required")
    return {"entity_id": entity_id, "schema_id": schema_id, "valid": True, "errors": []}


def _simulate_scenario(params: dict) -> dict:
    scenario_id = params.get("scenario_id", "")
    parameters = params.get("parameters", "{}")
    if not scenario_id:
        raise ValueError("scenario_id is required")
    return {"scenario_id": scenario_id, "parameters": parameters, "outcome": "PASS", "steps": []}


def _get_validation_result(params: dict) -> dict:
    result_id = params.get("result_id", "")
    if not result_id:
        raise ValueError("result_id is required")
    return {"result_id": result_id, "status": "COMPLETED", "passed": True, "failures": []}


def _list_validation_rules(params: dict) -> dict:
    category = params.get("category", "")
    return {"category": category, "rules": [], "total": 0}


def _run_validation_suite(params: dict) -> dict:
    suite_id = params.get("suite_id", "")
    entity_id = params.get("entity_id", "")
    if not suite_id or not entity_id:
        raise ValueError("suite_id and entity_id are required")
    return {"suite_id": suite_id, "entity_id": entity_id, "run_id": f"run-{entity_id[:6]}", "status": "STARTED"}
