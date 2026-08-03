from __future__ import annotations
from learning_intelligence.application.di import Container, set_container
from learning_intelligence.infrastructure.memory_store import (
    InMemoryCache,
    InMemoryFeedbackRepository,
    InMemoryKnowledgeChangeRepository,
    InMemoryLearningReportRepository,
    LoggingEventPublisher,
)
from learning_intelligence.settings import Settings, get_settings

async def build_container(*, memory: bool = True, settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    c = Container(
        settings=settings,
        reports=InMemoryLearningReportRepository(),
        feedback=InMemoryFeedbackRepository(),
        knowledge=InMemoryKnowledgeChangeRepository(),
        cache=InMemoryCache(),
        events=LoggingEventPublisher(),
    )
    set_container(c)
    return c
