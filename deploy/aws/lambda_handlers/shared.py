"""Shared utilities for all GIE Bedrock Agent Lambda handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_event(event: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Return (action_group, function_name, parameters_dict) from a Bedrock Agent event."""
    action_group = event.get("actionGroup", "")
    function = event.get("function", "")
    raw_params = event.get("parameters", [])
    params: dict[str, Any] = {}
    for p in raw_params:
        val = p.get("value", "")
        ptype = p.get("type", "string")
        if ptype == "integer":
            try:
                val = int(val)
            except (TypeError, ValueError):
                pass
        elif ptype == "number":
            try:
                val = float(val)
            except (TypeError, ValueError):
                pass
        elif ptype == "boolean":
            val = str(val).lower() == "true"
        params[p["name"]] = val
    return action_group, function, params


def ok(action_group: str, function: str, body: Any) -> dict[str, Any]:
    """Return a successful Bedrock Agent action-group response."""
    if not isinstance(body, str):
        body = json.dumps(body, default=str)
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {"body": body}
                }
            },
        },
    }


def err(action_group: str, function: str, message: str) -> dict[str, Any]:
    """Return an error Bedrock Agent response (REPROMPT so agent retries gracefully)."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseState": "REPROMPT",
                "responseBody": {
                    "TEXT": {"body": f"Error: {message}"}
                },
            },
        },
    }
