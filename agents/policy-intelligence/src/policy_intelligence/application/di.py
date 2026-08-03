from __future__ import annotations
from dataclasses import dataclass
from policy_intelligence.application.explain_policy import ExplainPolicyHandler
from policy_intelligence.application.generate_policy import GeneratePolicyHandler
from policy_intelligence.domain.ports import CacheStore, DecisionRepository, EventPublisher
from policy_intelligence.settings import Settings

@dataclass
class Container:
    settings: Settings
    decisions: DecisionRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def generate(self) -> GeneratePolicyHandler:
        return GeneratePolicyHandler(decisions=self.decisions, cache=self.cache, events=self.events, settings=self.settings)

    @property
    def explain(self) -> ExplainPolicyHandler:
        return ExplainPolicyHandler(self.decisions)

_container: Container | None = None

def set_container(c: Container) -> None:
    global _container
    _container = c

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
