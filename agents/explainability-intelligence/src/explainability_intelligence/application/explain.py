from __future__ import annotations
import time
from gie_contracts.explainability import ExplainRequest, ExplanationReport
from gie_contracts.explainability_events import ExplanationGenerated
from gie_observability.logging import get_logger
from explainability_intelligence.domain.engine import explain_decision
from explainability_intelligence.domain.ports import CacheStore, EventPublisher, ExplanationRepository
from gie_llm import BedrockLLMClient
from explainability_intelligence.domain.llm_enhancer import enhance_explanation_report
from explainability_intelligence.settings import Settings
from explainability_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class ExplainHandler:
    def __init__(self, *, explanations: ExplanationRepository, cache: CacheStore, events: EventPublisher, settings: Settings):
        self._explanations = explanations
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

    async def handle(self, request: ExplainRequest, *, actor: str, correlation_id: str) -> ExplanationReport:
        started = time.perf_counter()
        report = explain_decision(request.bundle)
        if request.persist:
            await self._explanations.save(report)
            await self._cache.set_json(
                f"explain:id:{report.explanation_id}",
                report.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            evt = ExplanationGenerated(
                tenant_id=report.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                explanation_id=report.explanation_id,
                decision_id=report.decision_id,
                audience_count=len(report.views),
                artifact_count=len(report.artifacts),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=str(report.explanation_id))
        if self._llm:
            report_dict = report.model_dump(mode="json")
            _enhanced = await enhance_explanation_report(report_dict, client=self._llm)
            report = report.model_copy(update={"llm_enhancement": {
                "narrative": _enhanced.get("llm_narrative", ""),
                "key_insights": _enhanced.get("llm_key_insights", []),
                "recommendations": _enhanced.get("llm_recommendations", []),
                "model": _enhanced.get("llm_model", ""),
            }})
        logger.info("explanation_generated", explanation_id=str(report.explanation_id), actor=actor)
        return report
