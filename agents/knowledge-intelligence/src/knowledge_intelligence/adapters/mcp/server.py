"""MCP tool definitions for Knowledge Intelligence Agent."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from gie_contracts.knowledge import (
    KnowledgeDomain,
    KnowledgeQueryRequest,
    KnowledgeUpsertRequest,
)
from gie_observability.logging import get_logger

from knowledge_intelligence.application.di import get_container

logger = get_logger(__name__)

TOOLS = [
    {
        "name": "knowledge_query",
        "description": "Explainable hybrid semantic search over the GIE knowledge graph",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "top_k": {"type": "integer", "default": 10},
                "version": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "knowledge_get_node",
        "description": "Fetch a knowledge node by id with evidence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string"},
                "version": {"type": "string"},
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "knowledge_upsert",
        "description": "Upsert knowledge nodes and edges into the versioned graph",
        "inputSchema": {
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "description": "KnowledgeUpsertRequest JSON",
                },
            },
            "required": ["payload"],
        },
    },
    {
        "name": "knowledge_diff_versions",
        "description": "Diff two published knowledge graph versions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_version": {"type": "string"},
                "to_version": {"type": "string"},
            },
            "required": ["from_version", "to_version"],
        },
    },
]


async def call_tool(
    name: str, arguments: dict[str, Any], *, tenant_id: str = "default"
) -> dict[str, Any]:
    container = get_container()
    if name == "knowledge_query":
        domains = [KnowledgeDomain(d) for d in arguments.get("domains", [])]
        req = KnowledgeQueryRequest(
            query=arguments["query"],
            domains=domains,
            top_k=int(arguments.get("top_k", 10)),
            version=arguments.get("version"),
        )
        result = await container.query_engine.query(
            req, tenant_id=tenant_id, correlation_id=uuid4().hex
        )
        return result.model_dump(mode="json")
    if name == "knowledge_get_node":
        node = await container.get_node.handle(
            arguments["node_id"], version=arguments.get("version")
        )
        return node.model_dump(mode="json")
    if name == "knowledge_upsert":
        payload = KnowledgeUpsertRequest.model_validate(arguments["payload"])
        return await container.upsert.handle(
            payload, tenant_id=tenant_id, actor="mcp", correlation_id=uuid4().hex
        )
    if name == "knowledge_diff_versions":
        diff = await container.diff_versions.handle(
            arguments["from_version"], arguments["to_version"]
        )
        return diff.model_dump(mode="json")
    raise ValueError(f"Unknown tool: {name}")


def list_tools() -> list[dict[str, Any]]:
    return TOOLS
