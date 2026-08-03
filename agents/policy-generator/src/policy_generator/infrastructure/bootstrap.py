from __future__ import annotations
from policy_generator.application.di import Container, set_container
from policy_generator.infrastructure.memory_store import InMemoryCache, InMemoryPolicyPackageRepository, LoggingEventPublisher
from policy_generator.settings import Settings, get_settings

async def build_container(*, memory: bool = True, settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    c = Container(settings=settings, packages=InMemoryPolicyPackageRepository(), cache=InMemoryCache(), events=LoggingEventPublisher())
    set_container(c)
    return c
