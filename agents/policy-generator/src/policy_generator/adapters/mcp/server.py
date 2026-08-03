from __future__ import annotations
from typing import Any
from uuid import UUID, uuid4
from gie_contracts.policy_generator import PolicyPackageGenerateRequest, PolicyGeneratorInputBundle, PolicyPackageValidateRequest
from policy_generator.application.di import get_container
from policy_generator.domain.templates import list_templates

TOOLS = [
    {"name": "policy_generate", "description": "Generate deployment-ready policies from recommendations", "inputSchema": {"type": "object", "properties": {"bundle": {"type": "object"}}, "required": ["bundle"]}},
    {"name": "policy_validate", "description": "Validate a policy package or content", "inputSchema": {"type": "object", "properties": {"package_id": {"type": "string"}, "content": {"type": "string"}, "format": {"type": "string"}}}},
    {"name": "policy_templates", "description": "List policy templates", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "policy_get", "description": "Get policy package by id", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]

async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "policy_generate":
        bundle = PolicyGeneratorInputBundle.model_validate(arguments["bundle"])
        pkg = await c.generate.handle(PolicyPackageGenerateRequest(bundle=bundle), actor="mcp", correlation_id=uuid4().hex)
        return pkg.model_dump(mode="json")
    if name == "policy_validate":
        req = PolicyPackageValidateRequest.model_validate(arguments)
        return await c.validate.handle(req, actor="mcp", correlation_id=uuid4().hex)
    if name == "policy_templates":
        return {"items": [t.model_dump(mode="json") for t in list_templates()]}
    if name == "policy_get":
        pkg = await c.packages.get(UUID(arguments["id"]))
        return pkg.model_dump(mode="json") if pkg else {}
    raise ValueError(name)

def list_tools():
    return TOOLS
