import pytest
from gie_contracts.orchestrator import AnalyzeRequest, ApprovalDecision, ExecutionMode, ExecutionStatus
from orchestrator.domain.invoker import SimulatedAgentInvoker

@pytest.mark.asyncio
async def test_sync_analyze_completes(container, sample_analyze):
    rec = await container.engine.analyze(sample_analyze)
    assert rec.status == ExecutionStatus.COMPLETED
    assert rec.result is not None
    assert rec.result.context
    assert rec.result.explainability
    assert len(rec.steps) == 9
    assert rec.confidence.score > 0
    assert rec.trace_id
    # second run should cache hit
    rec2 = await container.engine.analyze(sample_analyze)
    assert rec2.cache_hits >= 1

@pytest.mark.asyncio
async def test_retry_on_transient(container, sample_analyze):
    inv = container.invoker
    assert isinstance(inv, SimulatedAgentInvoker)
    inv.arm_transient_failure("context")
    rec = await container.engine.analyze(sample_analyze)
    assert rec.status == ExecutionStatus.COMPLETED
    ctx = next(s for s in rec.steps if s.step_id == "context")
    assert ctx.retries >= 1

@pytest.mark.asyncio
async def test_approval_gate(container):
    req = AnalyzeRequest(
        tenant_id="acme",
        source={"path": "/x"},
        mode=ExecutionMode.SYNC,
        require_human_approval=True,
        approval_gates=["validation"],
        cache=False,
    )
    rec = await container.engine.analyze(req)
    assert rec.status == ExecutionStatus.WAITING_APPROVAL
    resumed = await container.engine.approve(
        ApprovalDecision(execution_id=rec.execution_id, step_id="validation", approved=True, actor="secops")
    )
    assert resumed.status == ExecutionStatus.COMPLETED
