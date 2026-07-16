"""List scans for a tenant."""

from __future__ import annotations

from dataclasses import dataclass

from gie_security.auth import AuthPrincipal
from gie_security.rbac import Permission, PermissionDeniedError, require_permission

from context_intelligence.domain.entities import ContextScan, ScanStatus
from context_intelligence.domain.ports import ContextRepository


@dataclass(frozen=True, slots=True)
class ListScansQuery:
    tenant_id: str
    principal: AuthPrincipal
    status: ScanStatus | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ListScansResult:
    scans: list[ContextScan]
    limit: int
    offset: int


class ListScansHandler:
    def __init__(self, *, repository: ContextRepository) -> None:
        self._repository = repository

    @require_permission(Permission.SCAN_READ)
    async def handle(self, query: ListScansQuery) -> ListScansResult:
        if query.principal.tenant_id != query.tenant_id:
            raise PermissionDeniedError(Permission.SCAN_READ, query.principal)

        scans = await self._repository.list_scans(
            query.tenant_id,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )
        return ListScansResult(scans=scans, limit=query.limit, offset=query.offset)
