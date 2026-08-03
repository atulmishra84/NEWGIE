from __future__ import annotations
from uuid import uuid4
from gie_contracts.explainability import ReasoningPathRequest
from gie_contracts.explainability_events import ReasoningPathBuilt
from gie_observability.logging import get_logger
from explainability_intelligence.domain.engine import build_reasoning_path
from explainability_intelligence.domain.ports import EventPublisher
from explainability_intelligence.settings import Settings
from explainability_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class ReasoningPathHandler:
    def __init__(self, *, events: EventPublisher, settings: Settings):
        self._events = events
        self._settings = settings

    async def handle(self, request: ReasoningPathRequest, *, actor: str, correlation_id: str) -> dict:
        result = build_reasoning_path(request)
        evt = ReasoningPathBuilt(
            tenant_id=request.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            explanation_id=None,
            step_count=result["step_count"],
        )
        await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=request.decision_id or uuid4().hex)
        logger.info("reasoning_path_built", steps=result["step_count"], actor=actor)
        return result
