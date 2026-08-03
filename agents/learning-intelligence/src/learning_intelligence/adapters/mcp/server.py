from __future__ import annotations
from typing import Any
from uuid import uuid4
from gie_contracts.learning import FeedbackRequest, LearnRequest, LearningInputBundle, FeedbackEvent
from learning_intelligence.application.di import get_container

TOOLS = [
    {"name": "learning_feedback", "description": "Submit learning feedback", "inputSchema": {"type": "object", "properties": {"event": {"type": "object"}}, "required": ["event"]}},
    {"name": "learning_learn", "description": "Run learning cycle", "inputSchema": {"type": "object", "properties": {"bundle": {"type": "object"}}, "required": ["bundle"]}},
    {"name": "learning_history", "description": "Learning history", "inputSchema": {"type": "object", "properties": {"tenant_id": {"type": "string"}}, "required": ["tenant_id"]}},
    {"name": "knowledge_changes", "description": "List knowledge changes", "inputSchema": {"type": "object", "properties": {"tenant_id": {"type": "string"}}, "required": ["tenant_id"]}},
]

async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    c = get_container()
    if name == "learning_feedback":
        event = FeedbackEvent.model_validate(arguments["event"])
        return await c.feedback_handler.handle(FeedbackRequest(event=event), actor="mcp", correlation_id=uuid4().hex)
    if name == "learning_learn":
        bundle = LearningInputBundle.model_validate(arguments["bundle"])
        report = await c.learn.handle(LearnRequest(bundle=bundle), actor="mcp", correlation_id=uuid4().hex)
        return report.model_dump(mode="json")
    if name == "learning_history":
        items = await c.reports.history(arguments["tenant_id"], agent_id=arguments.get("agent_id"))
        return {"items": [i.model_dump(mode="json") for i in items]}
    if name == "knowledge_changes":
        items = await c.knowledge.list(arguments["tenant_id"], status=arguments.get("status"))
        return {"items": [i.model_dump(mode="json") for i in items]}
    raise ValueError(name)

def list_tools():
    return TOOLS
