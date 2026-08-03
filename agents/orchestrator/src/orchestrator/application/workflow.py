from __future__ import annotations
from gie_contracts.orchestrator import ApprovalDecision, ExecutionRecord, WorkflowRequest
from gie_observability.logging import get_logger
from orchestrator.domain.engine import OrchestratorEngine

logger = get_logger(__name__)

class WorkflowHandler:
    def __init__(self, engine: OrchestratorEngine):
        self._engine = engine

    async def handle(self, request: WorkflowRequest, *, actor: str) -> ExecutionRecord:
        logger.info("workflow_requested", tenant=request.tenant_id, workflow=request.workflow.workflow_id, actor=actor)
        return await self._engine.workflow(request)

    async def approve(self, decision: ApprovalDecision) -> ExecutionRecord:
        return await self._engine.approve(decision)
