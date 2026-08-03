from __future__ import annotations
from typing import Any
from uuid import UUID, uuid4
from gie_contracts.integration import AuthTokenRequest, ConnectRequest, PlatformId, SyncRequest, WebhookIngressRequest
from integration_intelligence.application.di import get_container
from integration_intelligence.domain.catalog import platform_catalog

TOOLS = [
    {"name": "list_platforms", "description": "List supported GIE integration platforms", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "connect_platform", "description": "Connect an enterprise platform", "inputSchema": {"type": "object", "properties": {"request": {"type": "object"}}, "required": ["request"]}},
    {"name": "sync_connection", "description": "Sync a connection", "inputSchema": {"type": "object", "properties": {"connection_id": {"type": "string"}, "tenant_id": {"type": "string"}}, "required": ["connection_id", "tenant_id"]}},
    {"name": "issue_auth_token", "description": "Issue OAuth/API key/JWT/mTLS token", "inputSchema": {"type": "object", "properties": {"request": {"type": "object"}}, "required": ["request"]}},
    {"name": "ingest_webhook", "description": "Ingest a webhook event", "inputSchema": {"type": "object", "properties": {"platform_id": {"type": "string"}, "payload": {"type": "object"}}, "required": ["platform_id"]}},
]

async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "list_platforms":
        plats = platform_catalog()
        return {"count": len(plats), "platforms": [p.model_dump(mode="json") for p in plats]}
    if name == "connect_platform":
        req = ConnectRequest.model_validate(arguments["request"])
        conn = await c.connect.handle(req, actor="mcp", correlation_id=uuid4().hex)
        return conn.model_dump(mode="json")
    if name == "sync_connection":
        req = SyncRequest(
            connection_id=UUID(arguments["connection_id"]),
            tenant_id=arguments["tenant_id"],
            direction=arguments.get("direction", "outbound"),
            payload=arguments.get("payload") or {},
        )
        result = await c.sync.handle(req, actor="mcp", correlation_id=uuid4().hex)
        return result.model_dump(mode="json")
    if name == "issue_auth_token":
        req = AuthTokenRequest.model_validate(arguments["request"])
        tok = await c.auth.handle(req, actor="mcp")
        return tok.model_dump(mode="json")
    if name == "ingest_webhook":
        pid = PlatformId(arguments["platform_id"])
        body = WebhookIngressRequest(tenant_id=arguments.get("tenant_id"), event_type=arguments.get("event_type", "generic"), payload=arguments.get("payload") or {})
        raw = b"{}"
        event = await c.webhook.handle(pid, body, raw_body=raw, actor="mcp", correlation_id=uuid4().hex, tenant_fallback=arguments.get("tenant_id") or "default")
        return event.model_dump(mode="json")
    raise ValueError(name)

def list_tools():
    return TOOLS
