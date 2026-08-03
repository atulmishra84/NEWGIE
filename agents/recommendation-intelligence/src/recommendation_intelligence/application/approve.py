from __future__ import annotations
from uuid import uuid4
from gie_contracts.recommendation import RecommendationApproveRequest, RecommendationReport
from gie_contracts.recommendation_events import RecommendationApproved
from gie_observability.logging import get_logger
from recommendation_intelligence.application.errors import NotFoundError, RecommendationError
from recommendation_intelligence.domain.engine import approve_recommendations
from recommendation_intelligence.domain.ports import CacheStore, EventPublisher, RecommendationReportRepository
from recommendation_intelligence.settings import Settings
from recommendation_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class ApproveRecommendationsHandler:
    def __init__(self, *, reports: RecommendationReportRepository, cache: CacheStore, events: EventPublisher, settings: Settings):
        self._reports = reports
        self._cache = cache
        self._events = events
        self._settings = settings

    async def handle(self, request: RecommendationApproveRequest, *, actor: str, correlation_id: str) -> RecommendationReport:
        prior = await self._reports.latest_for_agent(request.tenant_id, request.agent_id)
        if not prior:
            raise NotFoundError(f"No recommendations for agent {request.agent_id}; generate first")
        if not request.approve_all and not request.recommendation_ids:
            raise RecommendationError("invalid_request", "Provide recommendation_ids or approve_all=true")
        report = approve_recommendations(
            prior,
            recommendation_ids=request.recommendation_ids,
            approve_all=request.approve_all,
        )
        # new report id for history
        report.report_id = uuid4()
        await self._reports.save(report)
        await self._cache.set_json(
            f"rec:latest:{report.tenant_id}:{report.agent_id}",
            report.model_dump(mode="json"),
            self._settings.cache_ttl_seconds,
        )
        approved_ids = [i.recommendation_id for i in report.recommendations if i.status.value == "approved"]
        evt = RecommendationApproved(
            tenant_id=report.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            agent_id=report.agent_id,
            report_id=report.report_id,
            approved_ids=approved_ids,
            actor=request.actor or actor,
        )
        await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=report.agent_id)
        logger.info("recommendations_approved", agent_id=report.agent_id, count=len(approved_ids), actor=actor)
        return report
