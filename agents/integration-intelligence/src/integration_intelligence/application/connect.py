from __future__ import annotations
from gie_contracts.integration import AuditLogEntry, ConnectRequest, IntegrationConnection
from gie_contracts.integration_events import IntegrationConnected
from gie_observability.logging import get_logger
from integration_intelligence.domain.connectors import ConnectorError, validate_connect
from integration_intelligence.domain.engine import build_connection
from integration_intelligence.domain.ports import AuditRepository, ConnectionRepository, EventPublisher, SecretStore
from integration_intelligence.application.errors import IntegrationError
from integration_intelligence.settings import Settings
from integration_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class ConnectHandler:
    def __init__(self, *, connections: ConnectionRepository, secrets: SecretStore, audits: AuditRepository, events: EventPublisher, settings: Settings):
        self._connections = connections
        self._secrets = secrets
        self._audits = audits
        self._events = events
        self._settings = settings

    async def handle(self, request: ConnectRequest, *, actor: str, correlation_id: str) -> IntegrationConnection:
        try:
            warnings = validate_connect(request)
        except ConnectorError as exc:
            raise IntegrationError("invalid_connect", str(exc)) from exc
        conn = build_connection(request, warnings=warnings)
        if not request.dry_run:
            if request.credentials:
                await self._secrets.put(f"conn:{conn.connection_id}", {"auth_method": request.auth_method.value, "credentials": request.credentials})
            await self._connections.save(conn)
            await self._audits.save(
                AuditLogEntry(
                    tenant_id=request.tenant_id,
                    actor=actor,
                    action="integration.connect",
                    resource_type="connection",
                    resource_id=str(conn.connection_id),
                    platform_id=conn.platform_id,
                    outcome="success",
                    detail={"warnings": warnings, "auth_method": request.auth_method.value},
                )
            )
            evt = IntegrationConnected(
                tenant_id=request.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                connection_id=conn.connection_id,
                platform_id=conn.platform_id.value,
                auth_method=conn.auth_method.value,
            )
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=str(conn.connection_id))
        logger.info("integration_connected", connection_id=str(conn.connection_id), platform=conn.platform_id.value)
        return conn
