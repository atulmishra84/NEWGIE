from __future__ import annotations
from typing import Any
from uuid import uuid4
from gie_contracts.policy import PolicyGenerateRequest, PolicyInputBundle, PolicyTarget, OutputFormat
from policy_intelligence.application.di import get_container

TOOLS = [
    {"name": "policy_generate", "description": "Generate deployment-ready guardrail policies from context/risk/compliance/knowledge/identity/business inputs",
     "inputSchema": {"type": "object", "properties": {"bundle": {"type": "object"}, "dry_run": {"type": "boolean"}}, "required": ["bundle"]}},
    {"name": "policy_explain", "description": "Explain why guardrails apply for a decision",
     "inputSchema": {"type": "object", "properties": {"decision_id": {"type": "string"}, "guardrail_id": {"type": "string"}}, "required": ["decision_id"]}},
    {"name": "policy_get_artifact", "description": "Fetch a generated policy artifact by filename",
     "inputSchema": {"type": "object", "properties": {"decision_id": {"type": "string"}, "filename": {"type": "string"}}, "required": ["decision_id", "filename"]}},
]

async def call_tool(name: str, arguments: dict[str, Any], *, tenant_id: str = "default") -> dict[str, Any]:
    c = get_container()
    if name == "policy_generate":
        bundle = PolicyInputBundle.model_validate(arguments["bundle"])
        if not bundle.tenant_id:
            bundle.tenant_id = tenant_id
        req = PolicyGenerateRequest(bundle=bundle, dry_run=bool(arguments.get("dry_run", False)))
        decision = await c.generate.handle(req, actor="mcp", correlation_id=uuid4().hex)
        return decision.model_dump(mode="json")
    if name == "policy_explain":
        from uuid import UUID
        return await c.explain.handle(UUID(arguments["decision_id"]), arguments.get("guardrail_id"))
    if name == "policy_get_artifact":
        from uuid import UUID
        d = await c.decisions.get(UUID(arguments["decision_id"]))
        art = next(a for a in d.artifacts if a.filename == arguments["filename"])
        return art.model_dump(mode="json")
    raise ValueError(f"Unknown tool: {name}")

def list_tools():
    return TOOLS
