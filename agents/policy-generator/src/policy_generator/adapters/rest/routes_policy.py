from __future__ import annotations
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.policy_generator import PolicyPackageGenerateRequest, PolicyPackageValidateRequest
from gie_security.auth import AuthPrincipal
from policy_generator.adapters.rest.deps import container_dep, require_perm
from policy_generator.application.di import Container
from policy_generator.application.errors import NotFoundError
from policy_generator.domain.rbac import PolicyGenPermission
from policy_generator.domain.templates import list_templates
from policy_generator.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1/policy", tags=["policy-generator"])
alias = APIRouter(prefix="/policy", tags=["policy-generator-alias"])

def _meta(started: float, confidence=None, reasoning=None) -> ResponseMeta:
    return ResponseMeta(
        trace_id=uuid4().hex,
        request_id=uuid4().hex,
        correlation_id=uuid4().hex,
        execution_ms=(time.perf_counter() - started) * 1000,
        confidence=confidence,
        reasoning_path=reasoning or [],
        agent_version=AGENT_VERSION,
        agent_name=AGENT_NAME,
    )

@router.post("/generate")
@alias.post("/generate")
async def generate(
    body: PolicyPackageGenerateRequest,
    principal: AuthPrincipal = Depends(require_perm(PolicyGenPermission.POLICY_GENERATE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    package = await container.generate.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=package, meta=_meta(started, package.confidence.score, package.reasoning_path))

@router.post("/validate")
@alias.post("/validate")
async def validate(
    body: PolicyPackageValidateRequest,
    principal: AuthPrincipal = Depends(require_perm(PolicyGenPermission.POLICY_VALIDATE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    result = await container.validate.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=result, meta=_meta(started))

@router.get("/templates")
@alias.get("/templates")
async def templates(principal: AuthPrincipal = Depends(require_perm(PolicyGenPermission.POLICY_READ))):
    started = time.perf_counter()
    items = list_templates()
    return ObservabilityEnvelope(data={"items": items, "count": len(items)}, meta=_meta(started))

@router.get("/{policy_id}")
@alias.get("/{policy_id}")
async def get_policy(
    policy_id: UUID,
    principal: AuthPrincipal = Depends(require_perm(PolicyGenPermission.POLICY_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    package = await container.packages.get(policy_id)
    if not package:
        raise NotFoundError(f"Policy package {policy_id} not found")
    return ObservabilityEnvelope(data=package, meta=_meta(started, package.confidence.score, package.reasoning_path))
