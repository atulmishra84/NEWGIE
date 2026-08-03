from __future__ import annotations
from typing import Any
from uuid import UUID, uuid4
from gie_contracts.explainability import ExplainRequest, ExplainabilityInputBundle, ReasoningPathRequest
from explainability_intelligence.application.di import get_container

TOOLS = [
    {"name": "explain_decision", "description": "Explain a GIE agent decision", "inputSchema": {"type": "object", "properties": {"bundle": {"type": "object"}}, "required": ["bundle"]}},
    {"name": "get_explanation", "description": "Fetch explanation by id", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "reasoning_path", "description": "Build reasoning path + mermaid/figma payload", "inputSchema": {"type": "object", "properties": {"tenant_id": {"type": "string"}, "steps": {"type": "array"}}, "required": ["tenant_id"]}},
    {"name": "figma_generate_diagram", "description": "Get FigJam generate_diagram payload", "inputSchema": {"type": "object", "properties": {"explanation_id": {"type": "string"}}}},
]

async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "explain_decision":
        bundle = ExplainabilityInputBundle.model_validate(arguments["bundle"])
        report = await c.explain.handle(ExplainRequest(bundle=bundle), actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    if name == "get_explanation":
        r = await c.explanations.get(UUID(arguments["id"]))
        return r.model_dump(mode="json") if r else {}
    if name == "reasoning_path":
        req = ReasoningPathRequest.model_validate(arguments)
        return await c.reasoning.handle(req, actor="mcp", correlation_id=uuid4().hex)
    if name == "figma_generate_diagram":
        if arguments.get("explanation_id"):
            r = await c.explanations.get(UUID(arguments["explanation_id"]))
            return r.figma_diagram if r else {}
        return {"error": "explanation_id required"}
    raise ValueError(name)

def list_tools():
    return TOOLS
