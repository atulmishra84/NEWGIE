from __future__ import annotations
from dataclasses import dataclass
from compliance_intelligence.application.analyze import AnalyzeComplianceHandler
from compliance_intelligence.application.validate import ValidateComplianceHandler
from compliance_intelligence.domain.ports import CacheStore, ComplianceReportRepository, EventPublisher
from compliance_intelligence.settings import Settings

@dataclass
class Container:
    settings: Settings
    reports: ComplianceReportRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def analyze(self) -> AnalyzeComplianceHandler:
        return AnalyzeComplianceHandler(reports=self.reports, cache=self.cache, events=self.events, settings=self.settings)

    @property
    def validate(self) -> ValidateComplianceHandler:
        return ValidateComplianceHandler(reports=self.reports, cache=self.cache, events=self.events, settings=self.settings)

_container = None

def set_container(c: Container) -> None:
    global _container
    _container = c

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
