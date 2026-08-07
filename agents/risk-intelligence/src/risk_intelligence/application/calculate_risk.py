from __future__ import annotations
import time
from gie_contracts.risk import RiskCalculateRequest, RiskReport
from gie_contracts.risk_events import RiskCalculationCompleted
from gie_llm import BedrockLLMClient
from gie_observability.logging import get_logger
from risk_intelligence.domain.engine import calculate_risk
from risk_intelligence.domain.llm_enhancer import enhance_risk_report
from risk_intelligence.domain.ports import CacheStore, EventPublisher, RiskReportRepository
from risk_intelligence.settings import Settings
from risk_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class CalculateRiskHandler:
    def __init__(self, *, reports: RiskReportRepository, cache: CacheStore, events: EventPublisher, settings: Settings):
        self._reports = reports
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

    async def handle(self, request: RiskCalculateRequest, *, actor: str, correlation_id: str) -> RiskReport:
        started = time.perf_counter()
        bundle = request.bundle
        prior = await self._reports.latest_for_agent(bundle.tenant_id, bundle.agent_id)
        report = calculate_risk(bundle, prior=prior)
        if self._llm:
            report_dict = report.model_dump(mode="json")
            enhanced = await enhance_risk_report(report_dict, client=self._llm)
            report = report.model_copy(update={"llm_enhancement": {
                "narrative": enhanced.get("llm_narrative", ""),
                "key_insights": enhanced.get("llm_key_insights", []),
                "recommendations": enhanced.get("llm_recommendations", []),
                "model": enhanced.get("llm_model", ""),
            }})
        if request.persist:
            await self._reports.save(report)
            await self._cache.set_json(
                f"risk:latest:{bundle.tenant_id}:{bundle.agent_id}",
                report.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            await self._cache.set_json(
                f"risk:bundle:{bundle.tenant_id}:{bundle.agent_id}",
                bundle.model_dump(mode="json"),
                86400 * 30,
            )
            evt = RiskCalculationCompleted(
                tenant_id=bundle.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                agent_id=bundle.agent_id,
                report_id=report.report_id,
                overall_ai_risk_score=report.overall_ai_risk_score,
                trust_score=report.trust_score,
                severity=report.severity.value,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=bundle.agent_id)
        logger.info("risk_calculated", agent_id=bundle.agent_id, overall=report.overall_ai_risk_score, actor=actor)
        return report
