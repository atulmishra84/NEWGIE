from __future__ import annotations
from typing import Any
from uuid import uuid4
from gie_contracts.risk import RiskCalculateRequest, RiskInputBundle, RiskRecalculateRequest
from risk_intelligence.application.di import get_container

TOOLS = [
    {"name": "risk_calculate", "description": "Calculate overall AI risk posture", "inputSchema": {"type": "object", "properties": {"bundle": {"type": "object"}}, "required": ["bundle"]}},
    {"name": "risk_recalculate", "description": "Dynamically recalculate risk for an agent", "inputSchema": {"type": "object", "properties": {"agent_id": {"type": "string"}, "tenant_id": {"type": "string"}, "org_risk_model": {"type": "object"}}, "required": ["agent_id", "tenant_id"]}},
    {"name": "risk_get", "description": "Get latest risk report for an agent", "inputSchema": {"type": "object", "properties": {"agent_id": {"type": "string"}, "tenant_id": {"type": "string"}}, "required": ["agent_id", "tenant_id"]}},
    {"name": "risk_remediation", "description": "Get remediation recommendations", "inputSchema": {"type": "object", "properties": {"agent_id": {"type": "string"}, "tenant_id": {"type": "string"}}, "required": ["agent_id", "tenant_id"]}},
]

async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "risk_calculate":
        bundle = RiskInputBundle.model_validate(arguments["bundle"])
        report = await c.calculate.handle(RiskCalculateRequest(bundle=bundle), actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    if name == "risk_recalculate":
        req = RiskRecalculateRequest(
            agent_id=arguments["agent_id"],
            tenant_id=arguments["tenant_id"],
            org_risk_model=arguments.get("org_risk_model"),
            bundle=RiskInputBundle.model_validate(arguments["bundle"]) if arguments.get("bundle") else None,
        )
        report = await c.recalculate.handle(req, actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    if name == "risk_get":
        report = await c.reports.latest_for_agent(arguments["tenant_id"], arguments["agent_id"])
        return report.model_dump(mode="json") if report else {}
    if name == "risk_remediation":
        report = await c.reports.latest_for_agent(arguments["tenant_id"], arguments["agent_id"])
        return {"remediations": [r.model_dump() for r in report.remediations]} if report else {}
    raise ValueError(name)

def list_tools():
    return TOOLS
