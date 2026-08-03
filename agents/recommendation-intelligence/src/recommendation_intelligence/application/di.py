from __future__ import annotations
from dataclasses import dataclass
from recommendation_intelligence.application.approve import ApproveRecommendationsHandler
from recommendation_intelligence.application.generate import GenerateRecommendationsHandler
from recommendation_intelligence.domain.ports import CacheStore, EventPublisher, RecommendationReportRepository
from recommendation_intelligence.settings import Settings

@dataclass
class Container:
    settings: Settings
    reports: RecommendationReportRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def generate(self) -> GenerateRecommendationsHandler:
        return GenerateRecommendationsHandler(reports=self.reports, cache=self.cache, events=self.events, settings=self.settings)

    @property
    def approve(self) -> ApproveRecommendationsHandler:
        return ApproveRecommendationsHandler(reports=self.reports, cache=self.cache, events=self.events, settings=self.settings)

_container = None

def set_container(c: Container) -> None:
    global _container
    _container = c

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
