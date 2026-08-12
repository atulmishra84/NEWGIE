from __future__ import annotations
from dataclasses import dataclass
from risk_intelligence.application.calculate_risk import CalculateRiskHandler
from risk_intelligence.application.recalculate_risk import RecalculateRiskHandler
from risk_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    RiskReportRepository,
)
from risk_intelligence.settings import Settings


@dataclass
class Container:
    settings: Settings
    reports: RiskReportRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def calculate(self) -> CalculateRiskHandler:
        return CalculateRiskHandler(
            reports=self.reports,
            cache=self.cache,
            events=self.events,
            settings=self.settings,
        )

    @property
    def recalculate(self) -> RecalculateRiskHandler:
        return RecalculateRiskHandler(
            reports=self.reports, calculate=self.calculate, cache=self.cache
        )


_container = None


def set_container(c: Container) -> None:
    global _container
    _container = c


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
