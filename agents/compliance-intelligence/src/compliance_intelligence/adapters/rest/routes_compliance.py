from __future__ import annotations
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, Query
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.compliance import ComplianceAnalyzeRequest, ComplianceValidateRequest
from gie_security.auth import AuthPrincipal
from compliance_intelligence.adapters.rest.deps import container_dep, require_perm
from compliance_intelligence.application.di import Container
from compliance_intelligence.application.errors import NotFoundError
from compliance_intelligence.domain.catalog import list_frameworks
from compliance_intelligence.domain.rbac import CompliancePermission
from compliance_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])
alias = APIRouter(prefix="/compliance", tags=["compliance-alias"])
fw_router = APIRouter(tags=["frameworks"])


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


@router.post("/analyze")
@alias.post("/analyze")
async def analyze(
    body: ComplianceAnalyzeRequest,
    principal: AuthPrincipal = Depends(
        require_perm(CompliancePermission.COMPLIANCE_ANALYZE)
    ),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    report = await container.analyze.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(
        data=report, meta=_meta(started, report.confidence.score, report.reasoning_path)
    )


@router.post("/validate")
@alias.post("/validate")
async def validate(
    body: ComplianceValidateRequest,
    principal: AuthPrincipal = Depends(
        require_perm(CompliancePermission.COMPLIANCE_VALIDATE)
    ),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    report = await container.validate.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(
        data=report, meta=_meta(started, report.confidence.score, report.reasoning_path)
    )


@router.get("/report")
@alias.get("/report")
async def report(
    application_id: str = Query(...),
    principal: AuthPrincipal = Depends(
        require_perm(CompliancePermission.COMPLIANCE_READ)
    ),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    r = await container.reports.latest(principal.tenant_id, application_id)
    if not r:
        raise NotFoundError(f"No compliance report for {application_id}")
    dashboard = {
        "report": r,
        "compliance_matrix": r.matrix,
        "gap_analysis": r.gaps,
        "evidence_report": r.evidence,
        "audit_package": r.audit_package,
        "control_mapping": r.control_mappings,
        "compliance_score": r.compliance_score,
        "applicable_frameworks": r.applicable_frameworks,
    }
    return ObservabilityEnvelope(
        data=dashboard, meta=_meta(started, r.confidence.score)
    )


@router.get("/evidence")
@alias.get("/evidence")
async def evidence(
    application_id: str = Query(...),
    control_id: str | None = None,
    principal: AuthPrincipal = Depends(
        require_perm(CompliancePermission.COMPLIANCE_READ)
    ),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    r = await container.reports.latest(principal.tenant_id, application_id)
    if not r:
        raise NotFoundError(f"No compliance report for {application_id}")
    items = r.evidence
    if control_id:
        items = [e for e in items if e.control_id == control_id]
    return ObservabilityEnvelope(
        data={"application_id": application_id, "items": items, "count": len(items)},
        meta=_meta(started),
    )


@fw_router.get("/frameworks")
@fw_router.get("/v1/frameworks")
async def frameworks(
    principal: AuthPrincipal = Depends(
        require_perm(CompliancePermission.COMPLIANCE_READ)
    ),
):
    started = time.perf_counter()
    items = list_frameworks()
    return ObservabilityEnvelope(
        data={
            "items": items,
            "count": len(items),
            "catalog_version": items[0]["catalog_version"] if items else None,
        },
        meta=_meta(started),
    )
