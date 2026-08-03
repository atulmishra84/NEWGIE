from __future__ import annotations
from dataclasses import dataclass
from explainability_intelligence.application.explain import ExplainHandler
from explainability_intelligence.application.reasoning import ReasoningPathHandler
from explainability_intelligence.domain.ports import CacheStore, EventPublisher, ExplanationRepository
from explainability_intelligence.settings import Settings

@dataclass
class Container:
    settings: Settings
    explanations: ExplanationRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def explain(self) -> ExplainHandler:
        return ExplainHandler(explanations=self.explanations, cache=self.cache, events=self.events, settings=self.settings)

    @property
    def reasoning(self) -> ReasoningPathHandler:
        return ReasoningPathHandler(events=self.events, settings=self.settings)

_container = None

def set_container(c: Container) -> None:
    global _container
    _container = c

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
