from __future__ import annotations
from dataclasses import dataclass
from integration_intelligence.application.auth import AuthTokenHandler
from integration_intelligence.application.connect import ConnectHandler
from integration_intelligence.application.sync import SyncHandler
from integration_intelligence.application.webhook import WebhookHandler
from integration_intelligence.domain.ports import (
    AuditRepository,
    CacheStore,
    ConnectionRepository,
    EventPublisher,
    SecretStore,
    SyncRepository,
    WebhookRepository,
)
from integration_intelligence.settings import Settings

@dataclass
class Container:
    settings: Settings
    connections: ConnectionRepository
    webhooks: WebhookRepository
    audits: AuditRepository
    syncs: SyncRepository
    secrets: SecretStore
    cache: CacheStore
    events: EventPublisher

    @property
    def connect(self) -> ConnectHandler:
        return ConnectHandler(connections=self.connections, secrets=self.secrets, audits=self.audits, events=self.events, settings=self.settings)

    @property
    def sync(self) -> SyncHandler:
        return SyncHandler(connections=self.connections, syncs=self.syncs, audits=self.audits, events=self.events, settings=self.settings)

    @property
    def webhook(self) -> WebhookHandler:
        return WebhookHandler(webhooks=self.webhooks, audits=self.audits, events=self.events, settings=self.settings)

    @property
    def auth(self) -> AuthTokenHandler:
        return AuthTokenHandler(audits=self.audits, settings=self.settings)

_container = None

def set_container(c: Container) -> None:
    global _container
    _container = c

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
