from __future__ import annotations
from dataclasses import dataclass
from policy_generator.application.generate import GeneratePolicyHandler
from policy_generator.application.validate import ValidatePolicyHandler
from policy_generator.domain.ports import CacheStore, EventPublisher, PolicyPackageRepository
from policy_generator.settings import Settings

@dataclass
class Container:
    settings: Settings
    packages: PolicyPackageRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def generate(self) -> GeneratePolicyHandler:
        return GeneratePolicyHandler(packages=self.packages, cache=self.cache, events=self.events, settings=self.settings)

    @property
    def validate(self) -> ValidatePolicyHandler:
        return ValidatePolicyHandler(packages=self.packages, events=self.events, settings=self.settings)

_container = None

def set_container(c: Container) -> None:
    global _container
    _container = c

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
