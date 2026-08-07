from __future__ import annotations
import time
from gie_contracts.learning import LearnRequest, LearningReport
from gie_contracts.learning_events import LearningCycleCompleted
from gie_observability.logging import get_logger
from learning_intelligence.domain.engine import run_learning_cycle
from learning_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    FeedbackRepository,
    KnowledgeChangeRepository,
    LearningReportRepository,
)
from gie_llm import BedrockLLMClient
from learning_intelligence.domain.llm_enhancer import enhance_learning_report
from learning_intelligence.settings import Settings
from learning_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class LearnHandler:
    def __init__(
        self,
        *,
        reports: LearningReportRepository,
        feedback: FeedbackRepository,
        knowledge: KnowledgeChangeRepository,
        cache: CacheStore,
        events: EventPublisher,
        settings: Settings,
    ):
        self._reports = reports
        self._feedback = feedback
        self._knowledge = knowledge
        self._cache = cache
        self._events = events
        self._settings = settings
        self._llm = BedrockLLMClient(
            region=settings.aws_region,
            model_id=settings.bedrock_model_id,
            max_tokens=settings.bedrock_max_tokens,
            temperature=settings.bedrock_temperature,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
        ) if settings.bedrock_enabled else None

    async def handle(self, request: LearnRequest, *, actor: str, correlation_id: str) -> LearningReport:
        started = time.perf_counter()
        # merge stored feedback if bundle empty-ish
        if not request.bundle.feedback and not any(
            [
                request.bundle.runtime_telemetry,
                request.bundle.security_incidents,
                request.bundle.false_positives,
                request.bundle.false_negatives,
            ]
        ):
            stored = await self._feedback.list(request.bundle.tenant_id, limit=200)
            request.bundle.feedback = stored
        report = run_learning_cycle(request.bundle, allow_auto_publish=self._settings.allow_auto_publish)
        if request.persist:
            await self._reports.save(report)
            if report.knowledge_changes:
                await self._knowledge.save_many(report.knowledge_changes)
            await self._cache.set_json(
                f"learn:latest:{report.tenant_id}:{report.agent_id or 'na'}",
                report.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            evt = LearningCycleCompleted(
                tenant_id=report.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                learning_id=report.learning_id,
                improved_count=len(report.improved_recommendations),
                knowledge_proposed=report.counts.get("knowledge_proposed", 0),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=str(report.learning_id))
        if self._llm:
            report_dict = report.model_dump(mode="json")
            _enhanced = await enhance_learning_report(report_dict, client=self._llm)
            report = report.model_copy(update={"llm_enhancement": {
                "narrative": _enhanced.get("llm_narrative", ""),
                "key_insights": _enhanced.get("llm_key_insights", []),
                "recommendations": _enhanced.get("llm_recommendations", []),
                "model": _enhanced.get("llm_model", ""),
            }})
        logger.info("learning_cycle_completed", learning_id=str(report.learning_id), actor=actor)
        return report
