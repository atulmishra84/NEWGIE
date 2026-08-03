from __future__ import annotations
from gie_contracts.validation import SimulateRequest, ValidationReport
from gie_contracts.validation_events import SimulationCompleted
from gie_observability.logging import get_logger
from validation_intelligence.domain.engine import simulate_only
from validation_intelligence.domain.ports import CacheStore, EventPublisher, ValidationReportRepository
from validation_intelligence.settings import Settings
from validation_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class SimulateHandler:
    def __init__(self, *, reports: ValidationReportRepository, cache: CacheStore, events: EventPublisher, settings: Settings):
        self._reports = reports
        self._cache = cache
        self._events = events
        self._settings = settings

    async def handle(self, request: SimulateRequest, *, actor: str, correlation_id: str) -> ValidationReport:
        report = simulate_only(request)
        await self._reports.save(report)
        failed = sum(1 for s in report.simulations if not s.passed)
        evt = SimulationCompleted(
            tenant_id=request.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            validation_id=report.validation_id,
            scenario_count=len(report.simulations),
            failed_scenarios=failed,
        )
        await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=str(report.validation_id))
        logger.info("simulation_completed", validation_id=str(report.validation_id), failed=failed, actor=actor)
        return report
