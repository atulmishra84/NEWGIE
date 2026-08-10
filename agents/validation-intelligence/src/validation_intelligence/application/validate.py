from __future__ import annotations
import time
from gie_contracts.validation import ValidateRequest, ValidationReport
from gie_contracts.validation_events import ValidationCompleted
from gie_observability.logging import get_logger
from validation_intelligence.domain.engine import validate_policies
from validation_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    ValidationReportRepository,
)
from gie_llm import BedrockLLMClient
from validation_intelligence.domain.llm_enhancer import enhance_validation_report
from validation_intelligence.settings import Settings
from validation_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)


class ValidateHandler:
    def __init__(
        self,
        *,
        reports: ValidationReportRepository,
        cache: CacheStore,
        events: EventPublisher,
        settings: Settings,
    ):
        self._reports = reports
        self._cache = cache
        self._events = events
        self._settings = settings
        self._llm = (
            BedrockLLMClient(
                region=settings.aws_region,
                model_id=settings.bedrock_model_id,
                max_tokens=settings.bedrock_max_tokens,
                temperature=settings.bedrock_temperature,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                aws_session_token=settings.aws_session_token,
            )
            if settings.bedrock_enabled
            else None
        )

    async def handle(
        self, request: ValidateRequest, *, actor: str, correlation_id: str
    ) -> ValidationReport:
        started = time.perf_counter()
        report = validate_policies(
            request.bundle, run_simulation=request.run_simulation
        )
        if request.persist:
            await self._reports.save(report)
            await self._cache.set_json(
                f"val:latest:{report.tenant_id}:{report.agent_id or 'na'}",
                report.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            evt = ValidationCompleted(
                tenant_id=report.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                validation_id=report.validation_id,
                verdict=report.verdict.value,
                approval_status=report.approval_status.value,
                finding_count=len(report.findings),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(
                self._settings.kafka_topic_events,
                evt.model_dump(mode="json"),
                key=str(report.validation_id),
            )
        if self._llm:
            report_dict = report.model_dump(mode="json")
            _enhanced = await enhance_validation_report(report_dict, client=self._llm)
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
            "validation_completed",
            validation_id=str(report.validation_id),
            verdict=report.verdict.value,
            actor=actor,
        )
        return report
