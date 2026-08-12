"""Lambda handler for Knowledge Intelligence Bedrock Agent action groups."""

from __future__ import annotations

import logging
from typing import Any

from shared import err, ok, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_FUNCTIONS = {
    "upsert_knowledge_node",
    "get_knowledge_node",
    "search_knowledge_graph",
    "delete_knowledge_node",
    "list_knowledge_nodes",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, params = parse_event(event)
    logger.info("action_group=%s function=%s params=%s", ag, fn, params)

    if fn not in _FUNCTIONS:
        return err(ag, fn, f"Unknown function: {fn}")

    try:
        if fn == "upsert_knowledge_node":
            return ok(ag, fn, _upsert_node(params))
        if fn == "get_knowledge_node":
            return ok(ag, fn, _get_node(params))
        if fn == "search_knowledge_graph":
            return ok(ag, fn, _search_graph(params))
        if fn == "delete_knowledge_node":
            return ok(ag, fn, _delete_node(params))
        if fn == "list_knowledge_nodes":
            return ok(ag, fn, _list_nodes(params))
    except Exception as exc:
        logger.exception("Error in %s", fn)
        return err(ag, fn, str(exc))

    return err(ag, fn, "Unhandled function")


def _upsert_node(params: dict) -> dict:
    node_id = params.get("node_id", "")
    node_type = params.get("node_type", "concept")
    label = params.get("label", "")
    if not node_id:
        raise ValueError("node_id is required")
    return {"node_id": node_id, "node_type": node_type, "label": label, "action": "upserted"}


def _get_node(params: dict) -> dict:
    node_id = params.get("node_id", "")
    if not node_id:
        raise ValueError("node_id is required")
    return {"node_id": node_id, "found": False}


def _search_graph(params: dict) -> dict:
    query = params.get("query", "")
    limit = params.get("limit", 10)
    return {"query": query, "results": [], "total": 0, "limit": limit}


def _delete_node(params: dict) -> dict:
    node_id = params.get("node_id", "")
    if not node_id:
        raise ValueError("node_id is required")
    return {"node_id": node_id, "deleted": True}


def _list_nodes(params: dict) -> dict:
    node_type = params.get("node_type", "")
    limit = params.get("limit", 20)
    return {"node_type": node_type, "nodes": [], "total": 0, "limit": limit}
