"""Start scan command — idempotent scan creation and enqueue."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from gie_contracts.events import ContextScanRequested
from gie_contracts.sources import ScanSource
from gie_observability import get_logger
from gie_security.auth import AuthPrincipal
from gie_security.rbac import Permission, PermissionDeniedError, require_permission

from context_intelligence.config import Settings
from context_intelligence.domain.entities import ContextScan, ScanStatus
from context_intelligence.domain.ports import (
    ContextRepository,
    EventPublisher,
    ScanEnqueuer,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class StartScanCommand:
    tenant_id: str
    source: ScanSource
    idempotency_key: str
    requested_by: str
    principal: AuthPrincipal
    webhook_url: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class StartScanResult:
    scan: ContextScan
    created: bool


class StartScanHandler:
    def __init__(
        self,
        *,
        repository: ContextRepository,
        event_publisher: EventPublisher,
        scan_enqueuer: ScanEnqueuer,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher
        self._scan_enqueuer = scan_enqueuer
        self._settings = settings

    @require_permission(Permission.SCAN_WRITE)
    async def handle(self, command: StartScanCommand) -> StartScanResult:
        if command.principal.tenant_id != command.tenant_id:
            raise PermissionDeniedError(Permission.SCAN_WRITE, command.principal)

        existing = await self._repository.get_scan_by_idempotency_key(
            command.tenant_id,
            command.idempotency_key,
        )
        if existing is not None:
            logger.info(
                "scan_idempotent_hit",
                scan_id=str(existing.scan_id),
                tenant_id=command.tenant_id,
                idempotency_key=command.idempotency_key,
            )
            return StartScanResult(scan=existing, created=False)

        correlation_id = command.correlation_id or uuid4().hex
        scan = ContextScan.create(
            tenant_id=command.tenant_id,
            source=command.source,
            idempotency_key=command.idempotency_key,
            requested_by=command.requested_by,
            webhook_url=command.webhook_url,
            correlation_id=correlation_id,
        )
        await self._repository.save_scan(scan)

        event = ContextScanRequested(
            tenant_id=command.tenant_id,
            correlation_id=correlation_id,
            producer_version=self._settings.agent_version,
            scan_id=scan.scan_id,
            source=command.source,
            idempotency_key=command.idempotency_key,
            requested_by=command.requested_by,
            webhook_url=command.webhook_url,
        )
        await self._event_publisher.publish(event)

        await self._scan_enqueuer.enqueue_execute(
            scan.scan_id,
            command.tenant_id,
            correlation_id,
        )

        logger.info(
            "scan_started",
            scan_id=str(scan.scan_id),
            tenant_id=command.tenant_id,
            source_type=command.source.type.value,
            status=ScanStatus.PENDING.value,
        )
        return StartScanResult(scan=scan, created=True)
