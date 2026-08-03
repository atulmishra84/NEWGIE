from __future__ import annotations
from recommendation_intelligence.application.di import Container, set_container
from recommendation_intelligence.infrastructure.memory_store import InMemoryCache, InMemoryRecommendationReportRepository, LoggingEventPublisher
from recommendation_intelligence.settings import Settings, get_settings

async def build_container(*, memory: bool = True, settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    c = Container(settings=settings, reports=InMemoryRecommendationReportRepository(), cache=InMemoryCache(), events=LoggingEventPublisher())
    set_container(c)
    return c
