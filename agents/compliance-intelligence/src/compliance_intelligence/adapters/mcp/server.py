from __future__ import annotations
from typing import Any
from uuid import uuid4
from gie_contracts.compliance import ComplianceAnalyzeRequest, ComplianceInputBundle, ComplianceValidateRequest
from compliance_intelligence.application.di import get_container
from compliance_intelligence.domain.catalog import list_frameworks

TOOLS = [
    {"name": "compliance_analyze", "description": "Analyze applicable regulations and gaps", "inputSchema": {"type": "object", "properties": {"bundle": {"type": "object"}}, "required": ["bundle"]}},
    {"name": "compliance_validate", "description": "Validate controls with evidence", "inputSchema": {"type": "object", "properties": {"tenant_id": {"type": "string"}, "application_id": {"type": "string"}, "implemented_controls": {"type": "array"}, "evidence": {"type": "array"}}, "required": ["tenant_id", "application_id"]}},
    {"name": "compliance_report", "description": "Get compliance dashboard/report", "inputSchema": {"type": "object", "properties": {"tenant_id": {"type": "string"}, "application_id": {"type": "string"}}, "required": ["tenant_id", "application_id"]}},
    {"name": "list_frameworks", "description": "List supported compliance frameworks", "inputSchema": {"type": "object", "properties": {}}},
]

async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "compliance_analyze":
        bundle = ComplianceInputBundle.model_validate(arguments["bundle"])
        report = await c.analyze.handle(ComplianceAnalyzeRequest(bundle=bundle), actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    if name == "compliance_validate":
        req = ComplianceValidateRequest.model_validate(arguments)
        report = await c.validate.handle(req, actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    if name == "compliance_report":
        r = await c.reports.latest(arguments["tenant_id"], arguments["application_id"])
        return r.model_dump(mode="json") if r else {}
    if name == "list_frameworks":
        return {"items": list_frameworks()}
    raise ValueError(name)

def list_tools():
    return TOOLS
