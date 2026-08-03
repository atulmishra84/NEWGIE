from __future__ import annotations
from typing import Any
from uuid import UUID
from gie_contracts.orchestrator import AnalyzeRequest
from orchestrator.application.di import get_container
from orchestrator.domain.graph import default_analyze_workflow, mermaid_execution_graph

TOOLS = [
    {"name": "analyze", "description": "Run unified GIE analysis pipeline", "inputSchema": {"type": "object", "properties": {"request": {"type": "object"}}, "required": ["request"]}},
    {"name": "get_execution", "description": "Get execution by id", "inputSchema": {"type": "object", "properties": {"execution_id": {"type": "string"}}, "required": ["execution_id"]}},
    {"name": "get_status", "description": "Orchestrator and agent health", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "execution_graph", "description": "Mermaid execution graph", "inputSchema": {"type": "object", "properties": {"parallel": {"type": "boolean"}}}},
]

async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "analyze":
        req = AnalyzeRequest.model_validate(arguments["request"])
        rec = await c.analyze.handle(req, actor="mcp")
        return rec.model_dump(mode="json")
    if name == "get_execution":
        rec = await c.executions.get(UUID(arguments["execution_id"]))
        return rec.model_dump(mode="json") if rec else {}
    if name == "get_status":
        from orchestrator.domain.router import default_health
        agents = default_health(c.settings)
        return {"healthy": True, "agents": [a.model_dump(mode="json") for a in agents], "active": await c.executions.count_active()}
    if name == "execution_graph":
        wf = default_analyze_workflow(parallel_enabled=bool(arguments.get("parallel", True)))
        return {"mermaid": mermaid_execution_graph(wf), "workflow_id": wf.workflow_id}
    raise ValueError(name)

def list_tools():
    return TOOLS
