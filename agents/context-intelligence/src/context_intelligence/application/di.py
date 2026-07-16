"""Simple dependency injection container for application services."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from context_intelligence.application.commands.cancel_scan import CancelScanHandler
from context_intelligence.application.commands.execute_scan import ExecuteScanHandler
from context_intelligence.application.commands.start_scan import StartScanHandler
from context_intelligence.application.normalizer import ContextModelNormalizer
from context_intelligence.application.pipeline import DetectionPipeline
from context_intelligence.application.queries.diff_models import DiffModelsHandler
from context_intelligence.application.queries.get_context_model import GetContextModelHandler
from context_intelligence.application.queries.get_scan import GetScanHandler
from context_intelligence.application.queries.list_scans import ListScansHandler
from context_intelligence.config import Settings, get_settings
from context_intelligence.domain.ports import (
    CacheStore,
    ContextRepository,
    Detector,
    EventPublisher,
    EvidenceVectorStore,
    GraphRepository,
    ScanEnqueuer,
    SourceReader,
    WorkspaceFactory,
)


@dataclass
class Infrastructure:
    """Concrete outbound adapters wired into the application layer."""

    source_reader: SourceReader
    detectors: Sequence[Detector]
    context_repository: ContextRepository
    graph_repository: GraphRepository
    evidence_vector_store: EvidenceVectorStore
    event_publisher: EventPublisher
    cache_store: CacheStore
    scan_enqueuer: ScanEnqueuer
    workspace_factory: WorkspaceFactory


@dataclass
class ApplicationContainer:
    """Resolved application handlers and shared services."""

    settings: Settings
    pipeline: DetectionPipeline
    start_scan: StartScanHandler
    execute_scan: ExecuteScanHandler
    cancel_scan: CancelScanHandler
    get_scan: GetScanHandler
    get_context_model: GetContextModelHandler
    list_scans: ListScansHandler
    diff_models: DiffModelsHandler


def create_container(
    infrastructure: Infrastructure,
    settings: Settings | None = None,
) -> ApplicationContainer:
    """Build the application service graph from infrastructure ports."""
    resolved_settings = settings or get_settings()
    normalizer = ContextModelNormalizer()

    pipeline = DetectionPipeline(
        source_reader=infrastructure.source_reader,
        detectors=infrastructure.detectors,
        normalizer=normalizer,
        context_repository=infrastructure.context_repository,
        graph_repository=infrastructure.graph_repository,
        evidence_vector_store=infrastructure.evidence_vector_store,
        event_publisher=infrastructure.event_publisher,
        cache_store=infrastructure.cache_store,
        settings=resolved_settings,
    )

    return ApplicationContainer(
        settings=resolved_settings,
        pipeline=pipeline,
        start_scan=StartScanHandler(
            repository=infrastructure.context_repository,
            event_publisher=infrastructure.event_publisher,
            scan_enqueuer=infrastructure.scan_enqueuer,
            settings=resolved_settings,
        ),
        execute_scan=ExecuteScanHandler(
            repository=infrastructure.context_repository,
            pipeline=pipeline,
            event_publisher=infrastructure.event_publisher,
            workspace_factory=infrastructure.workspace_factory,
            settings=resolved_settings,
        ),
        cancel_scan=CancelScanHandler(repository=infrastructure.context_repository),
        get_scan=GetScanHandler(repository=infrastructure.context_repository),
        get_context_model=GetContextModelHandler(
            repository=infrastructure.context_repository,
            cache=infrastructure.cache_store,
        ),
        list_scans=ListScansHandler(repository=infrastructure.context_repository),
        diff_models=DiffModelsHandler(repository=infrastructure.context_repository),
    )
