from __future__ import annotations
from dataclasses import dataclass
from validation_intelligence.application.simulate import SimulateHandler
from validation_intelligence.application.validate import ValidateHandler
from validation_intelligence.domain.ports import CacheStore, EventPublisher, ValidationReportRepository
from validation_intelligence.settings import Settings

@dataclass
class Container:
    settings: Settings
    reports: ValidationReportRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def validate(self) -> ValidateHandler:
        return ValidateHandler(reports=self.reports, cache=self.cache, events=self.events, settings=self.settings)

    @property
    def simulate(self) -> SimulateHandler:
        return SimulateHandler(reports=self.reports, cache=self.cache, events=self.events, settings=self.settings)

_container = None

def set_container(c: Container) -> None:
    global _container
    _container = c

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
