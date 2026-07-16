"""Detection pipeline: materialize → detect → merge → normalize → persist."""

from __future__ import annotations

import time
from collections.abc import Sequence

from gie_contracts.context_model import ContextModel
from gie_contracts.events import ContextModelUpdated
from gie_observability import DETECTOR_RUNS, PIPELINE_STAGE_DURATION, get_logger, traced
from gie_observability.context import get_context

from context_intelligence.application.normalizer import ContextModelNormalizer
from context_intelligence.config import Settings
from context_intelligence.domain.entities import ContextScan
from context_intelligence.domain.findings import DetectionFinding, merge_findings
from context_intelligence.domain.ports import (
    CacheStore,
    ContextRepository,
    Detector,
    EventPublisher,
    EvidenceVectorStore,
    GraphRepository,
    ScanWorkspace,
    SourceReader,
)

logger = get_logger(__name__)


class DetectionPipeline:
    """Orchestrates scan stages across outbound ports."""

    def __init__(
        self,
        *,
        source_reader: SourceReader,
        detectors: Sequence[Detector],
        normalizer: ContextModelNormalizer,
        context_repository: ContextRepository,
        graph_repository: GraphRepository,
        evidence_vector_store: EvidenceVectorStore,
        event_publisher: EventPublisher,
        cache_store: CacheStore,
        settings: Settings,
    ) -> None:
        self._source_reader = source_reader
        self._detectors = list(detectors)
        self._normalizer = normalizer
        self._context_repository = context_repository
        self._graph_repository = graph_repository
        self._evidence_vector_store = evidence_vector_store
        self._event_publisher = event_publisher
        self._cache_store = cache_store
        self._settings = settings

    @traced("detection_pipeline.run")
    async def run(self, scan: ContextScan, workspace: ScanWorkspace) -> ContextModel:
        source_digest = await self._stage(
            "materialize",
            self._materialize(scan, workspace),
        )
        findings = await self._stage("detect", self._detect(workspace))
        merged = merge_findings(findings)
        model = await self._stage(
            "normalize",
            self._normalize(merged, scan, source_digest),
        )
        await self._stage("persist", self._persist(scan, model, merged))
        await self._stage("events", self._publish_events(scan, model))
        await self._stage("cache", self._cache_model(scan, model))
        return model

    async def _stage(self, name: str, coro):
        start = time.perf_counter()
        try:
            result = await coro
            return result
        finally:
            PIPELINE_STAGE_DURATION.labels(stage=name).observe(time.perf_counter() - start)

    async def _materialize(self, scan: ContextScan, workspace: ScanWorkspace) -> str:
        digest = await self._source_reader.materialize(scan.source, workspace)
        logger.info(
            "source_materialized",
            scan_id=str(scan.scan_id),
            source_type=scan.source.type.value,
            digest=digest,
            workspace=str(workspace.path),
        )
        return digest

    async def _detect(self, workspace: ScanWorkspace) -> list[DetectionFinding]:
        all_findings: list[DetectionFinding] = []
        ctx = get_context()

        for detector in self._detectors:
            detector_id = detector.detector_id
            try:
                findings = list(await detector.detect(workspace.path))
                all_findings.extend(findings)
                DETECTOR_RUNS.labels(detector_id=detector_id, status="success").inc()
                if ctx is not None:
                    ctx.add_reasoning(
                        detector_id=detector_id,
                        action="detect",
                        detail=f"Emitted {len(findings)} findings",
                        confidence=max((f.confidence for f in findings), default=0.0),
                    )
                logger.debug(
                    "detector_completed",
                    detector_id=detector_id,
                    findings_count=len(findings),
                )
            except Exception:
                DETECTOR_RUNS.labels(detector_id=detector_id, status="error").inc()
                logger.exception("detector_failed", detector_id=detector_id)
                raise

        return all_findings

    async def _normalize(
        self,
        findings: list[DetectionFinding],
        scan: ContextScan,
        source_digest: str,
    ) -> ContextModel:
        return self._normalizer.normalize(
            findings,
            scan,
            source_digest,
            agent_version=self._settings.agent_version,
        )

    async def _persist(
        self,
        scan: ContextScan,
        model: ContextModel,
        findings: list[DetectionFinding],
    ) -> None:
        await self._context_repository.save_model(model)
        await self._graph_repository.upsert_graph(
            scan.scan_id,
            scan.tenant_id,
            model.graph,
        )
        stored = await self._evidence_vector_store.upsert_evidence(
            scan.scan_id,
            scan.tenant_id,
            findings,
        )
        logger.info(
            "scan_persisted",
            scan_id=str(scan.scan_id),
            model_id=str(model.model_id),
            evidence_vectors=stored,
        )

    async def _publish_events(self, scan: ContextScan, model: ContextModel) -> None:
        correlation_id = scan.correlation_id or scan.scan_id.hex
        summary = {
            "frameworks": len(model.ai.frameworks),
            "apis": len(model.interfaces.apis),
            "secrets": len(model.data.secret_findings),
            "graph_nodes": len(model.graph.nodes),
        }
        await self._event_publisher.publish(
            ContextModelUpdated(
                tenant_id=scan.tenant_id,
                correlation_id=correlation_id,
                producer_version=self._settings.agent_version,
                model_id=model.model_id,
                scan_id=scan.scan_id,
                version=model.version,
                schema_version=model.schema_version,
                summary=summary,
            )
        )

    async def _cache_model(self, scan: ContextScan, model: ContextModel) -> None:
        cache_key = f"ctxmodel:{scan.tenant_id}:{model.model_id}"
        await self._cache_store.set(
            cache_key,
            model.model_dump_json().encode("utf-8"),
            ttl_seconds=300,
        )
