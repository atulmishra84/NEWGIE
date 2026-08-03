from __future__ import annotations
from compliance_intelligence.application.di import Container, set_container
from compliance_intelligence.infrastructure.memory_store import InMemoryCache, InMemoryComplianceReportRepository, LoggingEventPublisher
from compliance_intelligence.settings import Settings, get_settings

async def build_container(*, memory: bool = True, settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    c = Container(settings=settings, reports=InMemoryComplianceReportRepository(), cache=InMemoryCache(), events=LoggingEventPublisher())
    set_container(c)
    return c
