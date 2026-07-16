"""Get scan by id query."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from gie_security.auth import AuthPrincipal
from gie_security.rbac import Permission, PermissionDeniedError, require_permission

from context_intelligence.application.errors import ScanNotFoundError
from context_intelligence.domain.entities import ContextScan
from context_intelligence.domain.ports import ContextRepository


@dataclass(frozen=True, slots=True)
class GetScanQuery:
    scan_id: UUID
    tenant_id: str
    principal: AuthPrincipal


class GetScanHandler:
    def __init__(self, *, repository: ContextRepository) -> None:
        self._repository = repository

    @require_permission(Permission.SCAN_READ)
    async def handle(self, query: GetScanQuery) -> ContextScan:
        if query.principal.tenant_id != query.tenant_id:
            raise PermissionDeniedError(Permission.SCAN_READ, query.principal)

        scan = await self._repository.get_scan(query.scan_id, query.tenant_id)
        if scan is None:
            raise ScanNotFoundError(query.scan_id, query.tenant_id)
        return scan
