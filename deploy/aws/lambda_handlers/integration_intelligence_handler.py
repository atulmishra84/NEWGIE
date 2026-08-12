"""Lambda handler for Integration Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "connect_integration",
    "sync_integration",
    "handle_webhook",
    "authenticate_integration",
    "list_integrations",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "connect_integration":
            return ok(ag, fn, _connect_integration(params))
        if fn == "sync_integration":
            return ok(ag, fn, _sync_integration(params))
        if fn == "handle_webhook":
            return ok(ag, fn, _handle_webhook(params))
        if fn == "authenticate_integration":
            return ok(ag, fn, _authenticate_integration(params))
        if fn == "list_integrations":
            return ok(ag, fn, _list_integrations(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _connect_integration(params: dict) -> dict:
    provider = params.get("provider", "")
    if not provider:
        raise ValueError("provider is required")
    return {"provider": provider, "integration_id": f"int-{provider[:6]}", "status": "CONNECTED"}


def _sync_integration(params: dict) -> dict:
    integration_id = params.get("integration_id", "")
    full_sync = params.get("full_sync", False)
    if not integration_id:
        raise ValueError("integration_id is required")
    return {"integration_id": integration_id, "full_sync": full_sync, "sync_id": f"sync-{integration_id[:6]}", "status": "STARTED"}


def _handle_webhook(params: dict) -> dict:
    provider = params.get("provider", "")
    event_type = params.get("event_type", "")
    if not provider or not event_type:
        raise ValueError("provider and event_type are required")
    return {"provider": provider, "event_type": event_type, "processed": True}


def _authenticate_integration(params: dict) -> dict:
    provider = params.get("provider", "")
    if not provider:
        raise ValueError("provider is required")
    return {"provider": provider, "authenticated": True, "token_expiry": ""}


def _list_integrations(params: dict) -> dict:
    status = params.get("status", "ACTIVE")
    return {"status": status, "integrations": [], "total": 0}
