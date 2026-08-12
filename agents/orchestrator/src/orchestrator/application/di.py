from __future__ import annotations
from dataclasses import dataclass
from orchestrator.application.analyze import AnalyzeHandler
from orchestrator.application.workflow import WorkflowHandler
from orchestrator.domain.engine import OrchestratorEngine
from orchestrator.domain.ports import (
    AgentInvoker,
    CacheStore,
    EventPublisher,
    ExecutionRepository,
    TraceRepository,
)
from orchestrator.settings import Settings


@dataclass
class Container:
    settings: Settings
    executions: ExecutionRepository
    traces: TraceRepository
    cache: CacheStore
    events: EventPublisher
    invoker: AgentInvoker
    engine: OrchestratorEngine

    @property
    def analyze(self) -> AnalyzeHandler:
        return AnalyzeHandler(self.engine)

    @property
    def workflow(self) -> WorkflowHandler:
        return WorkflowHandler(self.engine)


_container = None


def set_container(c: Container) -> None:
    global _container
    _container = c


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
