"""Workflow orchestration engine: state machine, parallel waves, caching, tracing."""

from __future__ import annotations
import asyncio
import hashlib
import json
import time
from typing import Any, AsyncIterator
from uuid import uuid4
from gie_contracts.orchestrator import (
    AgentId,
    AnalyzeRequest,
    ApprovalDecision,
    Confidence,
    ExecutionMode,
    ExecutionRecord,
    ExecutionStatus,
    ExecutionTrace,
    StepExecution,
    StepStatus,
    TraceSpan,
    UnifiedAnalysisResult,
    WorkflowDefinition,
    WorkflowRequest,
    utcnow,
)
from gie_contracts.orchestrator_events import ApprovalRequested, ExecutionCompleted, ExecutionStarted, StepCompleted
from orchestrator.domain.graph import default_analyze_workflow, topological_waves
from orchestrator.domain.retry import with_retry
from orchestrator.domain.router import resolve_version
from orchestrator.domain.ports import AgentInvoker, CacheStore, EventPublisher, ExecutionRepository, TraceRepository
from gie_llm import BedrockLLMClient
from orchestrator.domain.llm_enhancer import enhance_analysis_result
from orchestrator.settings import Settings
from orchestrator.version import AGENT_VERSION

_RESULT_KEYS = {
    AgentId.CONTEXT: "context",
    AgentId.KNOWLEDGE: "knowledge",
    AgentId.RISK: "risk",
    AgentId.COMPLIANCE: "compliance",
    AgentId.POLICY: "policy",
    AgentId.RECOMMENDATION: "recommendation",
    AgentId.GENERATOR: "generator",
    AgentId.VALIDATION: "validation",
    AgentId.EXPLAINABILITY: "explainability",
}

class OrchestratorEngine:
    def __init__(
        self,
        *,
        executions: ExecutionRepository,
        traces: TraceRepository,
        cache: CacheStore,
        events: EventPublisher,
        invoker: AgentInvoker,
        settings: Settings,
    ):
        self._executions = executions
        self._traces = traces
        self._cache = cache
        self._events = events
        self._invoker = invoker
        self._settings = settings
        self._approvals: dict[tuple[str, str], asyncio.Event] = {}
        self._llm = BedrockLLMClient(
            region=settings.aws_region,
            model_id=settings.bedrock_model_id,
            max_tokens=settings.bedrock_max_tokens,
            temperature=settings.bedrock_temperature,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
        ) if settings.bedrock_enabled else None

    def _cache_key(self, tenant_id: str, step_id: str, payload: dict[str, Any]) -> str:
        blob = json.dumps({"t": tenant_id, "s": step_id, "p": payload}, sort_keys=True, default=str)
        return "orch:" + hashlib.sha256(blob.encode()).hexdigest()[:32]

    def _apply_approval_gates(self, workflow: WorkflowDefinition, request_gates: list[str], require_all: bool) -> WorkflowDefinition:
        gates = set(request_gates)
        if require_all and not gates:
            gates = {"validation"}  # default human gate before explainability publish
        steps = []
        for s in workflow.steps:
            sc = s.model_copy()
            if sc.step_id in gates:
                sc.requires_approval = True
            steps.append(sc)
        return workflow.model_copy(update={"steps": steps})

    async def analyze(self, request: AnalyzeRequest) -> ExecutionRecord:
        parallel = bool(request.options.get("parallel", True))
        workflow = default_analyze_workflow(parallel_enabled=parallel)
        if request.options.get("sequential"):
            from orchestrator.domain.graph import sequential_analyze_workflow
            workflow = sequential_analyze_workflow()
        workflow = self._apply_approval_gates(workflow, request.approval_gates, request.require_human_approval)
        record = await self._run(
            tenant_id=request.tenant_id,
            workflow=workflow,
            mode=request.mode,
            input_payload={"source": request.source, "options": request.options, "metadata": request.metadata},
            agent_versions=request.agent_versions,
            cache=request.cache,
            timeout_ms=request.timeout_ms,
            correlation_id=request.correlation_id or uuid4().hex,
            metadata=request.metadata,
        )
        if self._llm and record.status == ExecutionStatus.COMPLETED:
            record_dict = record.model_dump(mode="json")
            enhanced = await enhance_analysis_result(record_dict, client=self._llm)
            record = record.model_copy(update={"llm_enhancement": {
                "narrative": enhanced.get("llm_narrative", ""),
                "key_insights": enhanced.get("llm_key_insights", []),
                "recommendations": enhanced.get("llm_recommendations", []),
                "model": enhanced.get("llm_model", ""),
            }})
        return record

    async def workflow(self, request: WorkflowRequest) -> ExecutionRecord:
        wf = self._apply_approval_gates(request.workflow, [], request.require_human_approval)
        return await self._run(
            tenant_id=request.tenant_id,
            workflow=wf,
            mode=request.mode,
            input_payload=request.input,
            agent_versions=request.agent_versions,
            cache=request.cache,
            timeout_ms=request.timeout_ms,
            correlation_id=request.correlation_id or uuid4().hex,
            metadata={},
        )

    async def approve(self, decision: ApprovalDecision) -> ExecutionRecord:
        key = (str(decision.execution_id), decision.step_id)
        ev = self._approvals.get(key)
        record = await self._executions.get(decision.execution_id)
        if not record:
            raise KeyError("execution not found")
        if not decision.approved:
            record.status = ExecutionStatus.CANCELLED
            record.error = f"Approval rejected for step {decision.step_id} by {decision.actor}"
            record.finished_at = utcnow()
            await self._executions.save(record)
            if ev:
                ev.set()
            return record
        record.metadata.setdefault("approvals", {})[decision.step_id] = {
            "actor": decision.actor,
            "note": decision.note,
            "approved": True,
        }
        await self._executions.save(record)
        if ev:
            ev.set()
        # If was waiting, resume
        if record.status == ExecutionStatus.WAITING_APPROVAL:
            return await self._resume(record)
        return record

    async def _resume(self, record: ExecutionRecord) -> ExecutionRecord:
        wf_data = record.metadata.get("workflow")
        workflow = WorkflowDefinition.model_validate(wf_data) if wf_data else default_analyze_workflow()
        return await self._continue(record, workflow, record.metadata.get("input") or {}, cache=True)

    async def _run(
        self,
        *,
        tenant_id: str,
        workflow: WorkflowDefinition,
        mode: ExecutionMode,
        input_payload: dict[str, Any],
        agent_versions: dict[str, str],
        cache: bool,
        timeout_ms: int | None,
        correlation_id: str,
        metadata: dict[str, Any],
    ) -> ExecutionRecord:
        record = ExecutionRecord(
            tenant_id=tenant_id,
            workflow_id=workflow.workflow_id,
            mode=mode,
            status=ExecutionStatus.RUNNING,
            started_at=utcnow(),
            correlation_id=correlation_id,
            agent_versions=agent_versions,
            metadata={
                **metadata,
                "workflow": workflow.model_dump(mode="json"),
                "input": input_payload,
                "approval_gates": [s.step_id for s in workflow.steps if s.requires_approval],
                "deps": {s.step_id: s.depends_on for s in workflow.steps},
            },
            steps=[
                StepExecution(step_id=s.step_id, agent_id=s.agent_id, version=resolve_version(s.agent_id, agent_versions, s.version))
                for s in workflow.steps
            ],
        )
        await self._executions.save(record)
        started_evt = ExecutionStarted(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            execution_id=record.execution_id,
            workflow_id=workflow.workflow_id,
            mode=mode.value,
        )
        await self._events.publish(self._settings.kafka_topic_events, started_evt.model_dump(mode="json"), key=str(record.execution_id))
        record.events_published += 1

        if mode == ExecutionMode.ASYNC:
            # fire-and-forget background continuation
            asyncio.create_task(self._continue(record, workflow, input_payload, cache=cache, global_timeout_ms=timeout_ms))
            record.status = ExecutionStatus.RUNNING
            await self._executions.save(record)
            return record

        return await self._continue(record, workflow, input_payload, cache=cache, global_timeout_ms=timeout_ms)

    async def stream_analyze(self, request: AnalyzeRequest) -> AsyncIterator[dict[str, Any]]:
        request.mode = ExecutionMode.STREAMING
        parallel = bool(request.options.get("parallel", True))
        workflow = default_analyze_workflow(parallel_enabled=parallel)
        workflow = self._apply_approval_gates(workflow, request.approval_gates, request.require_human_approval)
        record = ExecutionRecord(
            tenant_id=request.tenant_id,
            workflow_id=workflow.workflow_id,
            mode=ExecutionMode.STREAMING,
            status=ExecutionStatus.RUNNING,
            started_at=utcnow(),
            correlation_id=request.correlation_id or uuid4().hex,
            agent_versions=request.agent_versions,
            metadata={"workflow": workflow.model_dump(mode="json"), "input": {"source": request.source}},
            steps=[
                StepExecution(step_id=s.step_id, agent_id=s.agent_id, version=resolve_version(s.agent_id, request.agent_versions, s.version))
                for s in workflow.steps
            ],
        )
        await self._executions.save(record)
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        await queue.put({"type": "execution_started", "execution_id": str(record.execution_id), "trace_id": record.trace_id})

        async def on_step(step: StepExecution):
            chunk = {"type": "step", "step_id": step.step_id, "status": step.status.value, "duration_ms": step.duration_ms}
            record.stream_chunks.append(chunk)
            await queue.put(chunk)
            return chunk

        async def runner():
            try:
                result = await self._continue(
                    record,
                    workflow,
                    {"source": request.source, "options": request.options},
                    cache=request.cache,
                    global_timeout_ms=request.timeout_ms,
                    stream_hook=on_step,
                )
                await queue.put(
                    {
                        "type": "execution_completed",
                        "execution_id": str(result.execution_id),
                        "status": result.status.value,
                        "confidence": result.confidence.score,
                    }
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(runner())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await task

    async def _continue(
        self,
        record: ExecutionRecord,
        workflow: WorkflowDefinition,
        input_payload: dict[str, Any],
        *,
        cache: bool,
        global_timeout_ms: int | None = None,
        stream_hook=None,
    ) -> ExecutionRecord:
        t0 = time.perf_counter()
        deadline = None
        if global_timeout_ms:
            deadline = time.perf_counter() + (global_timeout_ms / 1000.0)
        trace = ExecutionTrace(trace_id=record.trace_id, execution_id=record.execution_id, tenant_id=record.tenant_id)
        step_map = {s.step_id: s for s in record.steps}
        outputs: dict[str, Any] = {}
        # seed outputs from already succeeded steps (resume)
        for s in record.steps:
            if s.status in {StepStatus.SUCCEEDED, StepStatus.CACHED} and s.output:
                outputs[s.step_id] = s.output

        # Resuming from an approval gate must leave waiting_approval
        if record.status == ExecutionStatus.WAITING_APPROVAL:
            record.status = ExecutionStatus.RUNNING
            record.error = None

        try:
            for wave in topological_waves(workflow):
                # skip completed
                pending_wave = [s for s in wave if step_map[s.step_id].status not in {StepStatus.SUCCEEDED, StepStatus.CACHED, StepStatus.SKIPPED}]
                if not pending_wave:
                    continue
                if deadline and time.perf_counter() > deadline:
                    record.status = ExecutionStatus.TIMED_OUT
                    record.error = "Global execution timeout exceeded"
                    break

                tasks = [
                    self._run_step(
                        record,
                        step_map[sd.step_id],
                        sd,
                        input_payload=input_payload,
                        upstream=outputs,
                        cache=cache,
                        trace=trace,
                    )
                    for sd in pending_wave
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                paused_for_approval = False
                for step_def, res in zip(pending_wave, results, strict=True):
                    step = step_map[step_def.step_id]
                    if isinstance(res, Exception):
                        step.status = StepStatus.FAILED
                        step.error = str(res)
                        if not step_def.optional:
                            record.status = ExecutionStatus.FAILED
                            record.error = f"Step {step.step_id} failed: {res}"
                    else:
                        # Prefer the returned step object (source of truth)
                        if isinstance(res, StepExecution):
                            step.status = res.status
                            step.output = res.output
                            step.error = res.error
                            step.retries = res.retries
                            step.duration_ms = res.duration_ms
                            step.cached = res.cached
                        if step.status in {StepStatus.SUCCEEDED, StepStatus.CACHED} and step.output:
                            outputs[step.step_id] = step.output
                        if stream_hook and step.status != StepStatus.WAITING_APPROVAL:
                            chunk = await stream_hook(step)
                            if chunk and chunk not in record.stream_chunks:
                                record.stream_chunks.append(chunk)
                    await self._executions.save(record)
                    if step.status == StepStatus.WAITING_APPROVAL:
                        record.status = ExecutionStatus.WAITING_APPROVAL
                        paused_for_approval = True
                    if record.status == ExecutionStatus.FAILED:
                        await self._traces.save(trace)
                        await self._finalize(record, outputs, t0, failed=True)
                        return record
                if paused_for_approval:
                    await self._executions.save(record)
                    await self._traces.save(trace)
                    return record

            # Completed all runnable waves without an open approval gate
            if record.status == ExecutionStatus.TIMED_OUT:
                record.finished_at = utcnow()
                record.duration_ms = int((time.perf_counter() - t0) * 1000)
                await self._executions.save(record)
            elif record.status == ExecutionStatus.CANCELLED:
                record.finished_at = utcnow()
                record.duration_ms = int((time.perf_counter() - t0) * 1000)
                await self._executions.save(record)
            else:
                await self._finalize(record, outputs, t0, failed=record.status == ExecutionStatus.FAILED)
            await self._traces.save(trace)
            return record
        except Exception as exc:  # noqa: BLE001
            record.status = ExecutionStatus.FAILED
            record.error = str(exc)
            record.finished_at = utcnow()
            record.duration_ms = int((time.perf_counter() - t0) * 1000)
            await self._executions.save(record)
            await self._traces.save(trace)
            return record

    async def _run_step(
        self,
        record: ExecutionRecord,
        step: StepExecution,
        step_def,
        *,
        input_payload: dict[str, Any],
        upstream: dict[str, Any],
        cache: bool,
        trace: ExecutionTrace,
    ) -> StepExecution:
        if step_def.requires_approval and not (record.metadata.get("approvals") or {}).get(step.step_id):
            # Non-blocking human gate: pause execution for GET /execution + POST /approve resume
            step.status = StepStatus.WAITING_APPROVAL
            step.started_at = utcnow()
            key = (str(record.execution_id), step.step_id)
            self._approvals.setdefault(key, asyncio.Event())
            evt = ApprovalRequested(
                tenant_id=record.tenant_id,
                correlation_id=record.correlation_id,
                producer_version=AGENT_VERSION,
                execution_id=record.execution_id,
                step_id=step.step_id,
            )
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=str(record.execution_id))
            record.events_published += 1
            return step

        payload = {
            "tenant_id": record.tenant_id,
            "execution_id": str(record.execution_id),
            "step_id": step.step_id,
            "input": input_payload,
            "upstream": {k: v for k, v in upstream.items()},
        }
        cache_key = self._cache_key(record.tenant_id, step.step_id, {"input": input_payload, "upstream_keys": sorted(upstream.keys()), "version": step.version})
        if cache:
            cached = await self._cache.get_json(cache_key)
            if cached:
                step.status = StepStatus.CACHED
                step.cached = True
                step.output = cached
                step.finished_at = utcnow()
                step.started_at = step.finished_at
                record.cache_hits += 1
                return step

        step.status = StepStatus.RUNNING
        step.started_at = utcnow()
        span = TraceSpan(span_id=step.span_id, parent_span_id=None, name=f"invoke:{step.agent_id.value}", agent_id=step.agent_id, started_at=step.started_at)
        t0 = time.perf_counter()
        try:
            async def call():
                return await self._invoker.invoke(
                    step.agent_id.value,
                    step.version,
                    payload,
                    timeout_ms=step_def.timeout_ms or self._settings.default_step_timeout_ms,
                )

            max_attempts = (step_def.retries if step_def.retries is not None else self._settings.default_retries) + 1
            out, retries = await with_retry(call, max_attempts=max_attempts, base_delay_ms=self._settings.retry_base_delay_ms)
            step.retries = retries
            step.attempt = retries + 1
            step.output = out
            step.status = StepStatus.SUCCEEDED
            if cache:
                await self._cache.set_json(cache_key, out, self._settings.cache_ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            step.status = StepStatus.FAILED
            step.error = str(exc)
            span.status = "error"
            raise
        finally:
            step.finished_at = utcnow()
            step.duration_ms = int((time.perf_counter() - t0) * 1000)
            span.finished_at = step.finished_at
            span.duration_ms = step.duration_ms
            span.attributes = {"retries": step.retries, "cached": step.cached, "version": step.version}
            if step.status != StepStatus.FAILED:
                span.status = "ok"
            trace.spans.append(span)
            evt = StepCompleted(
                tenant_id=record.tenant_id,
                correlation_id=record.correlation_id,
                producer_version=AGENT_VERSION,
                execution_id=record.execution_id,
                step_id=step.step_id,
                agent_id=step.agent_id.value,
                status=step.status.value,
                duration_ms=step.duration_ms,
            )
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=str(record.execution_id))
            record.events_published += 1
        return step

    async def _finalize(self, record: ExecutionRecord, outputs: dict[str, Any], t0: float, *, failed: bool) -> None:
        result = UnifiedAnalysisResult()
        for agent_id, field in _RESULT_KEYS.items():
            # map by step_id == agent value
            data = outputs.get(agent_id.value) or {}
            setattr(result, field, data)
        record.result = result
        if failed:
            if record.status != ExecutionStatus.TIMED_OUT:
                record.status = ExecutionStatus.FAILED
        else:
            failed_steps = [s for s in record.steps if s.status == StepStatus.FAILED]
            if failed_steps:
                record.status = ExecutionStatus.PARTIAL
            else:
                record.status = ExecutionStatus.COMPLETED
        scores = [float((s.output or {}).get("confidence") or 0.8) for s in record.steps if s.status in {StepStatus.SUCCEEDED, StepStatus.CACHED}]
        avg = sum(scores) / len(scores) if scores else 0.5
        record.confidence = Confidence(score=round(avg, 3), rationale="Mean confidence across succeeded agent steps")
        record.reasoning_path = [
            {"step": s.step_id, "agent": s.agent_id.value, "status": s.status.value, "ms": s.duration_ms}
            for s in record.steps
        ]
        record.finished_at = utcnow()
        record.duration_ms = int((time.perf_counter() - t0) * 1000)
        await self._executions.save(record)
        done = ExecutionCompleted(
            tenant_id=record.tenant_id,
            correlation_id=record.correlation_id,
            producer_version=AGENT_VERSION,
            execution_id=record.execution_id,
            status=record.status.value,
            duration_ms=record.duration_ms,
        )
        await self._events.publish(self._settings.kafka_topic_events, done.model_dump(mode="json"), key=str(record.execution_id))
        record.events_published += 1
        await self._executions.save(record)
