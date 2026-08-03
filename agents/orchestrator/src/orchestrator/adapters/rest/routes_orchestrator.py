from __future__ import annotations
import asyncio
import json
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.orchestrator import (
    AnalyzeRequest,
    ApprovalDecision,
    BatchAnalyzeRequest,
    ExecutionMode,
    OrchestratorStatus,
    WorkflowRequest,
)
from gie_security.auth import AuthPrincipal
from orchestrator.adapters.rest.deps import container_dep, require_perm
from orchestrator.application.di import Container
from orchestrator.application.errors import NotFoundError
from orchestrator.domain.graph import default_analyze_workflow, mermaid_execution_graph, topological_waves
from orchestrator.domain.rbac import OrchestratorPermission
from orchestrator.domain.router import default_health
from orchestrator.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1", tags=["orchestrator"])
alias = APIRouter(tags=["orchestrator-alias"])

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
    body: AnalyzeRequest,
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_ANALYZE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    if body.mode == ExecutionMode.STREAMING:
        async def event_gen():
            async for chunk in container.engine.stream_analyze(body):
                yield f"data: {json.dumps(chunk)}\n\n"
        return StreamingResponse(event_gen(), media_type="text/event-stream")
    record = await container.analyze.handle(body, actor=principal.subject_id)
    return ObservabilityEnvelope(
        data=record,
        meta=_meta(started, record.confidence.score, record.reasoning_path),
    )

@router.post("/analyze/batch")
@alias.post("/analyze/batch")
async def analyze_batch(
    body: BatchAnalyzeRequest,
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_ANALYZE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    records = await container.analyze.batch(body, actor=principal.subject_id)
    return ObservabilityEnvelope(data={"items": records, "count": len(records)}, meta=_meta(started))

@router.post("/workflow")
@alias.post("/workflow")
async def workflow(
    body: WorkflowRequest,
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_WORKFLOW)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    record = await container.workflow.handle(body, actor=principal.subject_id)
    return ObservabilityEnvelope(data=record, meta=_meta(started, record.confidence.score, record.reasoning_path))

@router.post("/approve")
@alias.post("/approve")
async def approve(
    body: ApprovalDecision,
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_APPROVE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.actor:
        body.actor = principal.subject_id
    try:
        record = await container.workflow.approve(body)
    except KeyError as exc:
        raise NotFoundError(str(exc)) from exc
    return ObservabilityEnvelope(data=record, meta=_meta(started))

@router.get("/status")
@alias.get("/status")
async def status(
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    agents = default_health(container.settings)
    # overlay live invoker health when not simulate-only
    try:
        live = await container.invoker.health()
        by_id = {a["agent_id"]: a for a in live}
        for a in agents:
            if a.agent_id.value in by_id:
                a.healthy = bool(by_id[a.agent_id.value].get("healthy", a.healthy))
    except Exception:  # noqa: BLE001
        pass
    data = OrchestratorStatus(
        version=AGENT_VERSION,
        healthy=True,
        agents=agents,
        active_executions=await container.executions.count_active(),
        queued_executions=0,
        cache_size=await container.cache.size(),
        uptime_hints={"simulate_agents": container.settings.simulate_agents, "max_parallel_steps": container.settings.max_parallel_steps},
    )
    return ObservabilityEnvelope(data=data, meta=_meta(started, 1.0))

@router.get("/execution/{execution_id}")
@alias.get("/execution/{execution_id}")
async def get_execution(
    execution_id: UUID,
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    record = await container.executions.get(execution_id)
    if not record or record.tenant_id != principal.tenant_id:
        raise NotFoundError(f"Execution {execution_id} not found")
    # brief wait for async tasks to flush
    if record.status.value == "running" and record.mode.value == "async":
        for _ in range(20):
            await asyncio.sleep(0.01)
            record = await container.executions.get(execution_id) or record
            if record.status.value != "running":
                break
    return ObservabilityEnvelope(data=record, meta=_meta(started, record.confidence.score, record.reasoning_path))

@router.get("/trace/{trace_id}")
@alias.get("/trace/{trace_id}")
async def get_trace(
    trace_id: str,
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    trace = await container.traces.get(trace_id)
    if not trace or trace.tenant_id != principal.tenant_id:
        raise NotFoundError(f"Trace {trace_id} not found")
    return ObservabilityEnvelope(data=trace, meta=_meta(started))

@router.get("/graph")
@alias.get("/graph")
async def execution_graph(
    parallel: bool = True,
    principal: AuthPrincipal = Depends(require_perm(OrchestratorPermission.ORCH_READ)),
):
    started = time.perf_counter()
    wf = default_analyze_workflow(parallel_enabled=parallel)
    waves = [[s.step_id for s in wave] for wave in topological_waves(wf)]
    return ObservabilityEnvelope(
        data={"workflow_id": wf.workflow_id, "mermaid": mermaid_execution_graph(wf), "waves": waves, "steps": wf.steps},
        meta=_meta(started, 1.0),
    )
