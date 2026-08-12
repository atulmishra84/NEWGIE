from __future__ import annotations
from orchestrator.application.di import Container, set_container
from orchestrator.domain.engine import OrchestratorEngine
from orchestrator.domain.invoker import build_invoker
from orchestrator.infrastructure.memory_store import (
    InMemoryCache,
    InMemoryExecutionRepository,
    InMemoryTraceRepository,
    LoggingEventPublisher,
)
from orchestrator.settings import Settings, get_settings


async def build_container(
    *, memory: bool = True, settings: Settings | None = None
) -> Container:
    settings = settings or get_settings()
    executions = InMemoryExecutionRepository()
    traces = InMemoryTraceRepository()
    cache = InMemoryCache()
    events = LoggingEventPublisher()
    invoker = build_invoker(settings)
    engine = OrchestratorEngine(
        executions=executions,
        traces=traces,
        cache=cache,
        events=events,
        invoker=invoker,
        settings=settings,
    )
    c = Container(
        settings=settings,
        executions=executions,
        traces=traces,
        cache=cache,
        events=events,
        invoker=invoker,
        engine=engine,
    )
    set_container(c)
    return c
