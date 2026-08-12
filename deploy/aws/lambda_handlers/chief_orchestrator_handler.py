"""Lambda handler for Chief Orchestrator Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "dispatch_agent_task",
    "get_agent_registry",
    "aggregate_agent_results",
    "scan_cve",
    "synthesize_voice_response",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "dispatch_agent_task":
            return ok(ag, fn, _dispatch_agent_task(params))
        if fn == "get_agent_registry":
            return ok(ag, fn, _get_agent_registry(params))
        if fn == "aggregate_agent_results":
            return ok(ag, fn, _aggregate_agent_results(params))
        if fn == "scan_cve":
            return ok(ag, fn, _scan_cve(params))
        if fn == "synthesize_voice_response":
            return ok(ag, fn, _synthesize_voice_response(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _dispatch_agent_task(params: dict) -> dict:
    agent_name = params.get("agent_name", "")
    task = params.get("task", "")
    priority = params.get("priority", "NORMAL")
    if not agent_name or not task:
        raise ValueError("agent_name and task are required")
    return {"agent_name": agent_name, "task": task, "priority": priority, "dispatch_id": f"disp-{agent_name[:6]}", "status": "DISPATCHED"}


def _get_agent_registry(params: dict) -> dict:
    include_inactive = params.get("include_inactive", False)
    return {"agents": [], "total": 15, "include_inactive": include_inactive}


def _aggregate_agent_results(params: dict) -> dict:
    session_id = params.get("session_id", "")
    if not session_id:
        raise ValueError("session_id is required")
    return {"session_id": session_id, "results": [], "consensus": "", "confidence": 0.0}


def _scan_cve(params: dict) -> dict:
    package = params.get("package", "")
    version = params.get("version", "")
    if not package:
        raise ValueError("package is required")
    return {"package": package, "version": version, "vulnerabilities": [], "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}}


def _synthesize_voice_response(params: dict) -> dict:
    text = params.get("text", "")
    voice_id = params.get("voice_id", "default")
    if not text:
        raise ValueError("text is required")
    return {"text": text, "voice_id": voice_id, "audio_url": "", "duration_seconds": 0}
