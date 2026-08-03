from __future__ import annotations
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.validation import SimulateRequest, ValidateRequest
from gie_security.auth import AuthPrincipal
from validation_intelligence.adapters.rest.deps import container_dep, require_perm
from validation_intelligence.application.di import Container
from validation_intelligence.application.errors import NotFoundError
from validation_intelligence.domain.rbac import ValidationPermission
from validation_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1", tags=["validation"])
alias = APIRouter(tags=["validation-alias"])

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

@router.post("/validate")
@alias.post("/validate")
async def validate(
    body: ValidateRequest,
    principal: AuthPrincipal = Depends(require_perm(ValidationPermission.VAL_RUN)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    report = await container.validate.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score, report.reasoning_path))

@router.post("/simulate")
@alias.post("/simulate")
async def simulate(
    body: SimulateRequest,
    principal: AuthPrincipal = Depends(require_perm(ValidationPermission.VAL_RUN)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    report = await container.simulate.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score, report.reasoning_path))

@router.get("/validation/report")
@alias.get("/validation/report")
async def validation_report(
    agent_id: str | None = None,
    principal: AuthPrincipal = Depends(require_perm(ValidationPermission.VAL_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    report = await container.reports.latest(principal.tenant_id, agent_id=agent_id)
    if not report:
        raise NotFoundError("No validation report found; run /validate first")
    dashboard = {
        "report": report,
        "verdict": report.verdict,
        "approval_status": report.approval_status,
        "findings": report.findings,
        "corrections": report.corrections,
        "simulations": report.simulations,
        "invalid_configurations": report.invalid_configurations,
        "counts": report.counts,
    }
    return ObservabilityEnvelope(data=dashboard, meta=_meta(started, report.confidence.score))

@router.get("/validation/{validation_id}")
@alias.get("/validation/{validation_id}")
async def get_validation(
    validation_id: UUID,
    principal: AuthPrincipal = Depends(require_perm(ValidationPermission.VAL_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    report = await container.reports.get(validation_id)
    if not report:
        raise NotFoundError(f"Validation {validation_id} not found")
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score, report.reasoning_path))
