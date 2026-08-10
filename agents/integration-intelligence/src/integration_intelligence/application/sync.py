from __future__ import annotations
from gie_contracts.integration import AuditLogEntry, SyncRequest, SyncResult
from gie_contracts.integration_events import (
    CircuitBreakerOpened,
    IntegrationSyncCompleted,
)
from gie_observability.logging import get_logger
from integration_intelligence.application.errors import NotFoundError
from integration_intelligence.domain.engine import run_sync
from integration_intelligence.domain.ports import (
    AuditRepository,
    ConnectionRepository,
    EventPublisher,
    SyncRepository,
)
from integration_intelligence.settings import Settings
from integration_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)


class SyncHandler:
    def __init__(
        self,
        *,
        connections: ConnectionRepository,
        syncs: SyncRepository,
        audits: AuditRepository,
        events: EventPublisher,
        settings: Settings,
    ):
        self._connections = connections
        self._syncs = syncs
        self._audits = audits
        self._events = events
        self._settings = settings

    async def handle(
        self, request: SyncRequest, *, actor: str, correlation_id: str
    ) -> SyncResult:
        if request.connection_id is None:
            raise NotFoundError("connection_id is required")
        conn = await self._connections.get(request.connection_id)
        if not conn or conn.tenant_id != request.tenant_id:
            raise NotFoundError(f"Connection {request.connection_id} not found")
        result = await run_sync(
            conn,
            request,
            failure_threshold=self._settings.circuit_failure_threshold,
            open_seconds=self._settings.circuit_open_seconds,
            max_attempts=self._settings.retry_max_attempts,
            base_delay_ms=self._settings.retry_base_delay_ms,
        )
        await self._connections.save(conn)
        await self._syncs.save(result)
        await self._audits.save(
            AuditLogEntry(
                tenant_id=request.tenant_id,
                actor=actor,
                action="integration.sync",
                resource_type="connection",
                resource_id=str(conn.connection_id),
                platform_id=conn.platform_id,
                outcome=result.status,
                detail={"sync_id": str(result.sync_id), "retries": result.retries},
            )
        )
        evt = IntegrationSyncCompleted(
            tenant_id=request.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            sync_id=result.sync_id,
            connection_id=conn.connection_id,
            status=result.status,
        )
        await self._events.publish(
            self._settings.kafka_topic_events,
            evt.model_dump(mode="json"),
            key=str(result.sync_id),
        )
        if result.status == "circuit_open" and conn.circuit_breaker_state == "open":
            cb = CircuitBreakerOpened(
                tenant_id=request.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                connection_id=conn.connection_id,
                platform_id=conn.platform_id.value,
                failure_count=conn.failure_count,
            )
            await self._events.publish(
                self._settings.kafka_topic_events,
                cb.model_dump(mode="json"),
                key=str(conn.connection_id),
            )
        logger.info(
            "integration_sync", sync_id=str(result.sync_id), status=result.status
        )
        return result
