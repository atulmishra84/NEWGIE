from __future__ import annotations
from integration_intelligence.application.di import Container, set_container
from integration_intelligence.infrastructure.memory_store import (
    InMemoryAuditRepository,
    InMemoryCache,
    InMemoryConnectionRepository,
    InMemorySecretStore,
    InMemorySyncRepository,
    InMemoryWebhookRepository,
    LoggingEventPublisher,
)
from integration_intelligence.settings import Settings, get_settings


async def build_container(
    *, memory: bool = True, settings: Settings | None = None
) -> Container:
    settings = settings or get_settings()
    c = Container(
        settings=settings,
        connections=InMemoryConnectionRepository(),
        webhooks=InMemoryWebhookRepository(),
        audits=InMemoryAuditRepository(),
        syncs=InMemorySyncRepository(),
        secrets=InMemorySecretStore(),
        cache=InMemoryCache(),
        events=LoggingEventPublisher(),
    )
    set_container(c)
    return c
