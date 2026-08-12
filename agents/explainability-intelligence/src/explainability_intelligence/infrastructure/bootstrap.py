from __future__ import annotations
from explainability_intelligence.application.di import Container, set_container
from explainability_intelligence.infrastructure.memory_store import (
    InMemoryCache,
    InMemoryExplanationRepository,
    LoggingEventPublisher,
)
from explainability_intelligence.settings import Settings, get_settings


async def build_container(
    *, memory: bool = True, settings: Settings | None = None
) -> Container:
    settings = settings or get_settings()
    c = Container(
        settings=settings,
        explanations=InMemoryExplanationRepository(),
        cache=InMemoryCache(),
        events=LoggingEventPublisher(),
    )
    set_container(c)
    return c
