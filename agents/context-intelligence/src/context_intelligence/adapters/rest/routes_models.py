"""Context model REST routes."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from gie_contracts.context_model import ContextModel
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta

from context_intelligence.adapters.rest.deps import (
    AuthContext,
    get_model_cache,
    get_repository,
    require_read,
)
from context_intelligence.domain.ports import ContextRepository, ModelCache
from context_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1/context-models", tags=["context-models"])


def _meta(request: Request, *, confidence: float | None = None) -> ResponseMeta:
    ctx = getattr(request.state, "obs_context", None)
    return ResponseMeta(
        trace_id=ctx.trace_id if ctx else "",
        request_id=ctx.request_id if ctx else "",
        correlation_id=ctx.correlation_id if ctx else "",
        execution_ms=getattr(request.state, "execution_ms", 0.0),
        confidence=confidence,
        agent_version=AGENT_VERSION,
        agent_name=AGENT_NAME,
        reasoning_path=ctx.reasoning_path if ctx else [],
    )


@router.get("/{model_id}")
async def get_context_model(
    request: Request,
    model_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
    cache: Annotated[ModelCache, Depends(get_model_cache)],
    version: int | None = Query(default=None),
) -> ObservabilityEnvelope[ContextModel]:
    cached = await cache.get(auth.tenant_id, model_id, version)
    if cached:
        model = ContextModel.model_validate_json(cached)
        return ObservabilityEnvelope(
            data=model, meta=_meta(request, confidence=model.overall_confidence())
        )

    model = await repo.get_context_model(model_id, auth.tenant_id, version=version)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Context model not found"
        )
    await cache.set(auth.tenant_id, model_id, version, model.model_dump_json())
    return ObservabilityEnvelope(
        data=model, meta=_meta(request, confidence=model.overall_confidence())
    )


@router.get("/{model_id}/versions")
async def list_model_versions(
    request: Request,
    model_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
) -> ObservabilityEnvelope[dict[str, Any]]:
    versions = await repo.list_model_versions(model_id, auth.tenant_id)
    if not versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Context model not found"
        )
    return ObservabilityEnvelope(
        data={"model_id": str(model_id), "versions": versions}, meta=_meta(request)
    )


@router.get("/{model_id}/diff")
async def diff_models(
    request: Request,
    model_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
    from_version: int = Query(alias="from"),
    to_version: int = Query(alias="to"),
) -> ObservabilityEnvelope[dict[str, Any]]:
    diff = await repo.diff_models(model_id, auth.tenant_id, from_version, to_version)
    if diff.get("error"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )
    return ObservabilityEnvelope(data=diff, meta=_meta(request))


@router.get("/{model_id}/findings")
async def list_findings(
    request: Request,
    model_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
    limit: int = Query(default=100, ge=1, le=500),
) -> ObservabilityEnvelope[dict[str, Any]]:
    findings = await repo.list_findings(
        tenant_id=auth.tenant_id, model_id=model_id, limit=limit
    )
    return ObservabilityEnvelope(data={"items": findings}, meta=_meta(request))
