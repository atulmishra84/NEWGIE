from __future__ import annotations
from gie_contracts.learning import FeedbackRequest
from gie_contracts.learning_events import FeedbackAccepted
from gie_observability.logging import get_logger
from learning_intelligence.domain.ports import EventPublisher, FeedbackRepository
from learning_intelligence.settings import Settings
from learning_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class FeedbackHandler:
    def __init__(self, *, feedback: FeedbackRepository, events: EventPublisher, settings: Settings):
        self._feedback = feedback
        self._events = events
        self._settings = settings

    async def handle(self, request: FeedbackRequest, *, actor: str, correlation_id: str) -> dict:
        event = request.event
        if request.persist:
            await self._feedback.save(event)
        evt = FeedbackAccepted(
            tenant_id=event.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            feedback_id=event.feedback_id,
            feedback_type=event.feedback_type.value,
        )
        await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=event.feedback_id)
        logger.info("feedback_accepted", feedback_id=event.feedback_id, type=event.feedback_type.value, actor=actor)
        return {"feedback": event, "accepted": True}
