from __future__ import annotations
from typing import Any
from uuid import UUID, uuid4
from gie_contracts.validation import (
    SimulateRequest,
    ValidateRequest,
    ValidationInputBundle,
)
from validation_intelligence.application.di import get_container

TOOLS = [
    {
        "name": "validate_policies",
        "description": "Validate policy package before deploy",
        "inputSchema": {
            "type": "object",
            "properties": {"bundle": {"type": "object"}},
            "required": ["bundle"],
        },
    },
    {
        "name": "simulate_policies",
        "description": "Simulate policy execution",
        "inputSchema": {
            "type": "object",
            "properties": {"tenant_id": {"type": "string"}},
            "required": ["tenant_id"],
        },
    },
    {
        "name": "get_validation",
        "description": "Get validation by id",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
]


async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "validate_policies":
        bundle = ValidationInputBundle.model_validate(arguments["bundle"])
        report = await c.validate.handle(
            ValidateRequest(bundle=bundle), actor="mcp", correlation_id=uuid4().hex
        )
        return report.model_dump(mode="json")
    if name == "simulate_policies":
        req = SimulateRequest.model_validate(arguments)
        report = await c.simulate.handle(req, actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    if name == "get_validation":
        r = await c.reports.get(UUID(arguments["id"]))
        return r.model_dump(mode="json") if r else {}
    raise ValueError(name)


def list_tools():
    return TOOLS
