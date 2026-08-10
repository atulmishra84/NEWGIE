"""Cancel scan command."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from gie_observability import get_logger
from gie_security.auth import AuthPrincipal
from gie_security.rbac import Permission, PermissionDeniedError, require_permission

from context_intelligence.application.errors import (
    ScanNotCancellableError,
    ScanNotFoundError,
)
from context_intelligence.domain.entities import ContextScan, ScanStatus
from context_intelligence.domain.ports import ContextRepository

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CancelScanCommand:
    scan_id: UUID
    tenant_id: str
    principal: AuthPrincipal
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CancelScanResult:
    scan: ContextScan


class CancelScanHandler:
    def __init__(self, *, repository: ContextRepository) -> None:
        self._repository = repository

    @require_permission(Permission.SCAN_CANCEL)
    async def handle(self, command: CancelScanCommand) -> CancelScanResult:
        if command.principal.tenant_id != command.tenant_id:
            raise PermissionDeniedError(Permission.SCAN_CANCEL, command.principal)

        scan = await self._repository.get_scan(command.scan_id, command.tenant_id)
        if scan is None:
            raise ScanNotFoundError(command.scan_id, command.tenant_id)

        if scan.status not in {ScanStatus.PENDING, ScanStatus.RUNNING}:
            raise ScanNotCancellableError(command.scan_id, scan.status.value)

        scan.mark_cancelled()
        if command.reason:
            scan.metadata["cancel_reason"] = command.reason
        await self._repository.update_scan(scan)

        logger.info(
            "scan_cancelled",
            scan_id=str(scan.scan_id),
            tenant_id=command.tenant_id,
            reason=command.reason,
        )
        return CancelScanResult(scan=scan)
