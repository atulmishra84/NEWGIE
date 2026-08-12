from __future__ import annotations
import time
from gie_contracts.recommendation import (
    RecommendationGenerateRequest,
    RecommendationReport,
)
from gie_contracts.recommendation_events import RecommendationGenerated
from gie_observability.logging import get_logger
from recommendation_intelligence.domain.engine import generate_recommendations
from recommendation_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    RecommendationReportRepository,
)
from gie_llm import AnthropicLLMClient
from recommendation_intelligence.domain.llm_enhancer import (
    enhance_recommendation_report,
)
from recommendation_intelligence.settings import Settings
from recommendation_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)


class GenerateRecommendationsHandler:
    def __init__(
        self,
        *,
        reports: RecommendationReportRepository,
        cache: CacheStore,
        events: EventPublisher,
        settings: Settings,
    ):
        self._reports = reports
        self._cache = cache
        self._events = events
        self._settings = settings
        self._llm = (
            AnthropicLLMClient(
                api_key=settings.anthropic_api_key,
                model_id=settings.anthropic_model_id,
                max_tokens=settings.anthropic_max_tokens,
            )
            if settings.anthropic_enabled
            else None
        )

    async def handle(
        self, request: RecommendationGenerateRequest, *, actor: str, correlation_id: str
    ) -> RecommendationReport:
        started = time.perf_counter()
        report = generate_recommendations(request.bundle)
        if request.persist:
            await self._reports.save(report)
            await self._cache.set_json(
                f"rec:latest:{report.tenant_id}:{report.agent_id}",
                report.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            evt = RecommendationGenerated(
                tenant_id=report.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                agent_id=report.agent_id,
                report_id=report.report_id,
                recommendation_count=len(report.recommendations),
                critical_count=report.counts.get("critical", 0),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(
                self._settings.kafka_topic_events,
                evt.model_dump(mode="json"),
                key=report.agent_id,
            )
        if self._llm:
            report_dict = report.model_dump(mode="json")
            _enhanced = await enhance_recommendation_report(
                report_dict, client=self._llm
            )
            report = report.model_copy(
                update={
                    "llm_enhancement": {
                        "narrative": _enhanced.get("llm_narrative", ""),
                        "key_insights": _enhanced.get("llm_key_insights", []),
                        "recommendations": _enhanced.get("llm_recommendations", []),
                        "model": _enhanced.get("llm_model", ""),
                    }
                }
            )
        logger.info(
            "recommendations_generated",
            agent_id=report.agent_id,
            count=len(report.recommendations),
            actor=actor,
        )
        return report
