from __future__ import annotations
from policy_intelligence.application.di import Container, set_container
from policy_intelligence.infrastructure.memory_store import InMemoryCache, InMemoryDecisionRepository, LoggingEventPublisher
from policy_intelligence.settings import Settings, get_settings

async def build_container(*, memory: bool = True, settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    # Production Postgres/Redis/Kafka can be swapped behind the same ports.
    # Memory mode is default for local/test and fully functional for policy generation.
    container = Container(
        settings=settings,
        decisions=InMemoryDecisionRepository(),
        cache=InMemoryCache(),
        events=LoggingEventPublisher(),
    )
    set_container(container)
    return container
