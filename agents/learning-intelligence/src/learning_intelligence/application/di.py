from __future__ import annotations
from dataclasses import dataclass
from learning_intelligence.application.approve import ApproveKnowledgeHandler
from learning_intelligence.application.feedback import FeedbackHandler
from learning_intelligence.application.learn import LearnHandler
from learning_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    FeedbackRepository,
    KnowledgeChangeRepository,
    LearningReportRepository,
)
from learning_intelligence.settings import Settings


@dataclass
class Container:
    settings: Settings
    reports: LearningReportRepository
    feedback: FeedbackRepository
    knowledge: KnowledgeChangeRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def feedback_handler(self) -> FeedbackHandler:
        return FeedbackHandler(
            feedback=self.feedback, events=self.events, settings=self.settings
        )

    @property
    def learn(self) -> LearnHandler:
        return LearnHandler(
            reports=self.reports,
            feedback=self.feedback,
            knowledge=self.knowledge,
            cache=self.cache,
            events=self.events,
            settings=self.settings,
        )

    @property
    def approve(self) -> ApproveKnowledgeHandler:
        return ApproveKnowledgeHandler(
            knowledge=self.knowledge, events=self.events, settings=self.settings
        )


_container = None


def set_container(c: Container) -> None:
    global _container
    _container = c


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
