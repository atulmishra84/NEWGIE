from __future__ import annotations
import time
from gie_contracts.compliance import ComplianceAnalyzeRequest, ComplianceReport
from gie_contracts.compliance_events import ComplianceAnalysisCompleted
from gie_observability.logging import get_logger
from compliance_intelligence.domain.engine import analyze_compliance
from compliance_intelligence.domain.ports import CacheStore, ComplianceReportRepository, EventPublisher
from compliance_intelligence.settings import Settings
from compliance_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class AnalyzeComplianceHandler:
    def __init__(self, *, reports: ComplianceReportRepository, cache: CacheStore, events: EventPublisher, settings: Settings):
        self._reports = reports
        self._cache = cache
        self._events = events
        self._settings = settings

    async def handle(self, request: ComplianceAnalyzeRequest, *, actor: str, correlation_id: str) -> ComplianceReport:
        started = time.perf_counter()
        report = analyze_compliance(request.bundle)
        if request.persist:
            await self._reports.save(report)
            await self._cache.set_json(
                f"comp:latest:{report.tenant_id}:{report.application_id}",
                report.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            evt = ComplianceAnalysisCompleted(
                tenant_id=report.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                application_id=report.application_id,
                report_id=report.report_id,
                compliance_score=report.compliance_score,
                gap_count=len(report.gaps),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=report.application_id)
        logger.info("compliance_analyzed", application_id=report.application_id, score=report.compliance_score, actor=actor)
        return report
