"""Get context model query with optional cache."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from gie_contracts.context_model import ContextModel
from gie_observability import MODEL_GETS, get_logger
from gie_security.auth import AuthPrincipal
from gie_security.rbac import Permission, PermissionDeniedError, require_permission

from context_intelligence.application.errors import ModelNotFoundError
from context_intelligence.domain.ports import CacheStore, ContextRepository

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class GetContextModelQuery:
    model_id: UUID
    tenant_id: str
    principal: AuthPrincipal
    use_cache: bool = True


@dataclass(frozen=True, slots=True)
class GetContextModelResult:
    model: ContextModel
    cache_hit: bool


class GetContextModelHandler:
    def __init__(
        self,
        *,
        repository: ContextRepository,
        cache: CacheStore,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    def _cache_key(self, tenant_id: str, model_id: UUID) -> str:
        return f"ctxmodel:{tenant_id}:{model_id}"

    @require_permission(Permission.MODEL_READ)
    async def handle(self, query: GetContextModelQuery) -> GetContextModelResult:
        if query.principal.tenant_id != query.tenant_id:
            raise PermissionDeniedError(Permission.MODEL_READ, query.principal)

        cache_key = self._cache_key(query.tenant_id, query.model_id)
        if query.use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                model = ContextModel.model_validate_json(cached)
                MODEL_GETS.labels(cache_hit="true").inc()
                logger.debug("context_model_cache_hit", model_id=str(query.model_id))
                return GetContextModelResult(model=model, cache_hit=True)

        model = await self._repository.get_model(query.model_id, query.tenant_id)
        if model is None:
            raise ModelNotFoundError(query.model_id, query.tenant_id)

        if query.use_cache:
            await self._cache.set(
                cache_key,
                model.model_dump_json().encode("utf-8"),
                ttl_seconds=self._cache_ttl_seconds,
            )

        MODEL_GETS.labels(cache_hit="false").inc()
        return GetContextModelResult(model=model, cache_hit=False)

    async def handle_by_scan(
        self,
        *,
        scan_id: UUID,
        tenant_id: str,
        principal: AuthPrincipal,
        use_cache: bool = True,
    ) -> GetContextModelResult:
        if principal.tenant_id != tenant_id:
            raise PermissionDeniedError(Permission.MODEL_READ, principal)

        model = await self._repository.get_model_by_scan(scan_id, tenant_id)
        if model is None:
            raise ModelNotFoundError(scan_id, tenant_id)

        return await self.handle(
            GetContextModelQuery(
                model_id=model.model_id,
                tenant_id=tenant_id,
                principal=principal,
                use_cache=use_cache,
            )
        )
