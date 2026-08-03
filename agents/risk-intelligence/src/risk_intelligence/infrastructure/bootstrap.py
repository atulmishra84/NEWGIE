from __future__ import annotations
from risk_intelligence.application.di import Container, set_container
from risk_intelligence.infrastructure.memory_store import InMemoryCache, InMemoryRiskReportRepository, LoggingEventPublisher
from risk_intelligence.settings import Settings, get_settings

async def build_container(*, memory: bool = True, settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    c = Container(
        settings=settings,
        reports=InMemoryRiskReportRepository(),
        cache=InMemoryCache(),
        events=LoggingEventPublisher(),
    )
    set_container(c)
    return c
