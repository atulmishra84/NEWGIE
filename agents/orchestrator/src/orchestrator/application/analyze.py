from __future__ import annotations
from gie_contracts.orchestrator import AnalyzeRequest, BatchAnalyzeRequest, ExecutionRecord
from gie_observability.logging import get_logger
from orchestrator.domain.engine import OrchestratorEngine
import asyncio

logger = get_logger(__name__)

class AnalyzeHandler:
    def __init__(self, engine: OrchestratorEngine):
        self._engine = engine

    async def handle(self, request: AnalyzeRequest, *, actor: str) -> ExecutionRecord:
        logger.info("analyze_requested", tenant=request.tenant_id, mode=request.mode.value, actor=actor)
        return await self._engine.analyze(request)

    async def batch(self, request: BatchAnalyzeRequest, *, actor: str) -> list[ExecutionRecord]:
        sem = asyncio.Semaphore(request.max_concurrency)

        async def one(item: AnalyzeRequest) -> ExecutionRecord:
            async with sem:
                item.mode = request.mode
                item.tenant_id = item.tenant_id or request.tenant_id
                return await self._engine.analyze(item)

        return list(await asyncio.gather(*[one(i) for i in request.items]))
