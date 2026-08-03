from __future__ import annotations
from gie_contracts.compliance import ComplianceValidateRequest, ControlStatus
from gie_contracts.compliance_events import ComplianceValidationCompleted
from gie_observability.logging import get_logger
from compliance_intelligence.application.errors import NotFoundError
from compliance_intelligence.domain.engine import validate_controls
from compliance_intelligence.domain.ports import CacheStore, ComplianceReportRepository, EventPublisher
from compliance_intelligence.settings import Settings
from compliance_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class ValidateComplianceHandler:
    def __init__(self, *, reports: ComplianceReportRepository, cache: CacheStore, events: EventPublisher, settings: Settings):
        self._reports = reports
        self._cache = cache
        self._events = events
        self._settings = settings

    async def handle(self, request: ComplianceValidateRequest, *, actor: str, correlation_id: str):
        prior = await self._reports.latest(request.tenant_id, request.application_id)
        if not prior:
            raise NotFoundError(f"No compliance report for application {request.application_id}; run analyze first")
        report = validate_controls(
            prior=prior,
            implemented_controls=request.implemented_controls,
            evidence=request.evidence,
            control_ids=request.control_ids or None,
        )
        await self._reports.save(report)
        await self._cache.set_json(
            f"comp:latest:{report.tenant_id}:{report.application_id}",
            report.model_dump(mode="json"),
            self._settings.cache_ttl_seconds,
        )
        missing = sum(1 for a in report.assessments if a.status == ControlStatus.MISSING)
        validated = sum(1 for a in report.assessments if a.status == ControlStatus.IMPLEMENTED)
        evt = ComplianceValidationCompleted(
            tenant_id=report.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            application_id=report.application_id,
            validated_controls=validated,
            still_missing=missing,
        )
        await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=report.application_id)
        logger.info("compliance_validated", application_id=report.application_id, validated=validated, actor=actor)
        return report
