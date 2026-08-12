from __future__ import annotations
from typing import Any
from uuid import uuid4
from gie_contracts.recommendation import (
    RecommendationApproveRequest,
    RecommendationGenerateRequest,
    RecommendationInputBundle,
)
from recommendation_intelligence.application.di import get_container

TOOLS = [
    {
        "name": "recommendations_generate",
        "description": "Generate prioritized recommendations",
        "inputSchema": {
            "type": "object",
            "properties": {"bundle": {"type": "object"}},
            "required": ["bundle"],
        },
    },
    {
        "name": "recommendations_get",
        "description": "Get latest recommendations for an agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "agent_id": {"type": "string"},
            },
            "required": ["tenant_id", "agent_id"],
        },
    },
    {
        "name": "recommendations_history",
        "description": "Recommendation history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "agent_id": {"type": "string"},
            },
        },
    },
    {
        "name": "recommendations_approve",
        "description": "Approve recommendations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "agent_id": {"type": "string"},
                "recommendation_ids": {"type": "array"},
                "approve_all": {"type": "boolean"},
            },
            "required": ["tenant_id", "agent_id"],
        },
    },
]


async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "recommendations_generate":
        bundle = RecommendationInputBundle.model_validate(arguments["bundle"])
        report = await c.generate.handle(
            RecommendationGenerateRequest(bundle=bundle),
            actor="mcp",
            correlation_id=uuid4().hex,
        )
        return report.model_dump(mode="json")
    if name == "recommendations_get":
        r = await c.reports.latest_for_agent(
            arguments["tenant_id"], arguments["agent_id"]
        )
        return r.model_dump(mode="json") if r else {}
    if name == "recommendations_history":
        items = await c.reports.history(
            arguments["tenant_id"], agent_id=arguments.get("agent_id")
        )
        return {"items": [i.model_dump(mode="json") for i in items]}
    if name == "recommendations_approve":
        req = RecommendationApproveRequest.model_validate(arguments)
        report = await c.approve.handle(req, actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    raise ValueError(name)


def list_tools():
    return TOOLS
