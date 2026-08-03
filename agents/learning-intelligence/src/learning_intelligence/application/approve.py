from __future__ import annotations
from gie_contracts.learning import ApproveKnowledgeRequest, KnowledgeChangeStatus, utcnow
from gie_contracts.learning_events import KnowledgeChangeApproved
from gie_observability.logging import get_logger
from learning_intelligence.application.errors import LearningError, NotFoundError
from learning_intelligence.domain.ports import EventPublisher, KnowledgeChangeRepository
from learning_intelligence.settings import Settings
from learning_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class ApproveKnowledgeHandler:
    def __init__(self, *, knowledge: KnowledgeChangeRepository, events: EventPublisher, settings: Settings):
        self._knowledge = knowledge
        self._events = events
        self._settings = settings

    async def handle(self, request: ApproveKnowledgeRequest, *, actor: str, correlation_id: str) -> dict:
        approved = []
        if request.approve_all_proposed:
            items = await self._knowledge.list(request.tenant_id, status=KnowledgeChangeStatus.PROPOSED.value, limit=500)
        else:
            if not request.change_ids:
                raise LearningError("invalid_request", "Provide change_ids or approve_all_proposed=true")
            items = []
            for cid in request.change_ids:
                ch = await self._knowledge.get(cid)
                if not ch:
                    raise NotFoundError(f"Knowledge change {cid} not found")
                items.append(ch)
        for ch in items:
            ch.status = KnowledgeChangeStatus.APPROVED
            ch.approved_by = request.actor or actor
            ch.approved_at = utcnow()
            # publishing is a separate explicit step conceptually; approval unlocks publish
            await self._knowledge.save(ch)
            approved.append(str(ch.change_id))
        evt = KnowledgeChangeApproved(
            tenant_id=request.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            change_ids=approved,
            actor=request.actor or actor,
        )
        await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=request.tenant_id)
        logger.info("knowledge_approved", count=len(approved), actor=actor)
        return {"approved_ids": approved, "count": len(approved), "note": request.note}
