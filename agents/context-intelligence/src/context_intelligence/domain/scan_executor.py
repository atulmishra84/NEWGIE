"""Scan execution orchestration."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from gie_contracts.context_model import (
    CONTEXT_MODEL_SCHEMA,
    Confidence,
    ContextModel,
    DetectedItem,
    IdentitySection,
    ProvenanceSection,
)
from gie_contracts.events import (
    ContextModelUpdated,
    ContextScanCompleted,
    ContextScanFailed,
    ContextScanRequested,
    ContextScanStarted,
)
from gie_contracts.sources import FolderSource, GitSource, ScanSource, SourceType
from gie_observability.logging import get_logger

from context_intelligence.domain.ports import (
    ContextRepository,
    EventPublisher,
    EvidenceVectorStore,
    GraphRepository,
    OutboxWriter,
)
from context_intelligence.version import AGENT_NAME, AGENT_VERSION

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _source_digest(source: ScanSource) -> str:
    payload = source.model_dump(mode="json")
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _resolve_scan_root(source: ScanSource) -> Path | None:
    if isinstance(source, FolderSource):
        return Path(source.path)
    if source.type in {
        SourceType.CURSOR_PROJECT,
        SourceType.VSCODE_WORKSPACE,
        SourceType.IDE_WORKSPACE,
    }:
        return Path(source.path)  # type: ignore[attr-defined]
    if source.type in {
        SourceType.LANGGRAPH,
        SourceType.OPENAI_AGENTS,
        SourceType.CREWAI,
        SourceType.AUTOGEN,
        SourceType.SEMANTIC_KERNEL,
        SourceType.AZURE_AI_FOUNDRY,
    }:
        return Path(source.path)  # type: ignore[attr-defined]
    if isinstance(source, GitSource):
        return None
    return None


def _detect_languages(root: Path) -> list[DetectedItem]:
    markers = {
        "requirements.txt": ("python", "pip"),
        "pyproject.toml": ("python", "poetry/uv"),
        "package.json": ("javascript", "npm"),
        "go.mod": ("go", "go modules"),
        "Cargo.toml": ("rust", "cargo"),
        "pom.xml": ("java", "maven"),
    }
    found: list[DetectedItem] = []
    for filename, (lang, pm) in markers.items():
        if (root / filename).exists():
            found.append(
                DetectedItem(
                    name=lang,
                    confidence=Confidence(score=0.85, rationale=f"Found {filename}"),
                    attributes={"package_manager_hint": pm},
                )
            )
    return found


def _build_minimal_context_model(
    *,
    scan_id: UUID,
    tenant_id: str,
    source: ScanSource,
    correlation_id: str,
) -> ContextModel:
    root = _resolve_scan_root(source)
    languages: list[DetectedItem] = []
    project_name: str | None = None
    if root and root.exists():
        languages = _detect_languages(root)
        project_name = root.name

    confidence = 0.6 if languages else 0.35
    return ContextModel(
        version=1,
        schema_version=CONTEXT_MODEL_SCHEMA,
        identity=IdentitySection(
            languages=languages,
            project_name=project_name,
            repository_url=getattr(source, "url", None),
        ),
        provenance=ProvenanceSection(
            agent_name=AGENT_NAME,
            agent_version=AGENT_VERSION,
            scan_id=scan_id,
            tenant_id=tenant_id,
            source_type=source.type.value,
            source_digest=_source_digest(source),
            confidence=Confidence(
                score=confidence, rationale="Baseline filesystem heuristics"
            ),
            detectors=["filesystem.language_markers"],
            reasoning_path=[],
        ),
    )


class ScanExecutor:
    """Runs a scan end-to-end and persists side effects."""

    def __init__(
        self,
        repo: ContextRepository,
        outbox: OutboxWriter,
        publisher: EventPublisher,
        graph: GraphRepository,
        vectors: EvidenceVectorStore,
        *,
        producer_version: str = AGENT_VERSION,
    ) -> None:
        self._repo = repo
        self._outbox = outbox
        self._publisher = publisher
        self._graph = graph
        self._vectors = vectors
        self._producer_version = producer_version

    async def execute(
        self, scan_id: UUID, tenant_id: str, correlation_id: str
    ) -> ContextModel:
        started = time.monotonic()
        scan = await self._repo.get_scan(scan_id, tenant_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        if scan["status"] in {"cancelled", "completed", "failed"}:
            logger.info(
                "scan_skip_terminal", scan_id=str(scan_id), status=scan["status"]
            )
            model_id = scan.get("model_id")
            if model_id and scan["status"] == "completed":
                model = await self._repo.get_context_model(
                    UUID(str(model_id)), tenant_id
                )
                if model:
                    return model
            raise ValueError(f"Scan {scan_id} is in terminal state: {scan['status']}")

        source_payload = scan.get("source")
        if not source_payload:
            raise ValueError("Scan missing source payload")
        from pydantic import TypeAdapter

        source = TypeAdapter(ScanSource).validate_python(source_payload)

        await self._repo.update_scan_status(
            scan_id, status="running", started_at=_utcnow()
        )
        started_event = ContextScanStarted(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            producer_version=self._producer_version,
            scan_id=scan_id,
        )
        await self._outbox.enqueue(started_event)
        await self._publisher.publish("context.scan.started", started_event)

        try:
            model = _build_minimal_context_model(
                scan_id=scan_id,
                tenant_id=tenant_id,
                source=source,
                correlation_id=correlation_id,
            )
            version = await self._repo.save_context_model(
                model, scan_id=scan_id, tenant_id=tenant_id
            )
            model.version = version

            root = _resolve_scan_root(source)
            if root and root.exists():
                readme = root / "README.md"
                if readme.exists():
                    text = readme.read_text(encoding="utf-8", errors="replace")[:4000]
                    evidence_id = hashlib.sha256(
                        f"{scan_id}:readme".encode()
                    ).hexdigest()[:16]
                    await self._repo.save_evidence(
                        scan_id=scan_id,
                        tenant_id=tenant_id,
                        evidence_id=evidence_id,
                        path=str(readme),
                        detector_id="filesystem.readme",
                        excerpt=text[:500],
                        excerpt_hash=hashlib.sha256(text.encode()).hexdigest(),
                    )
                    await self._vectors.upsert_evidence(
                        evidence_id=evidence_id,
                        tenant_id=tenant_id,
                        scan_id=scan_id,
                        text=text,
                        metadata={
                            "path": str(readme),
                            "detector_id": "filesystem.readme",
                        },
                    )

            await self._graph.project_context_model(model, tenant_id)
            duration_ms = int((time.monotonic() - started) * 1000)
            await self._repo.update_scan_status(
                scan_id,
                status="completed",
                model_id=model.model_id,
                completed_at=_utcnow(),
            )

            completed_event = ContextScanCompleted(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                producer_version=self._producer_version,
                scan_id=scan_id,
                model_id=model.model_id,
                model_version=version,
                confidence=model.overall_confidence(),
                duration_ms=duration_ms,
            )
            updated_event = ContextModelUpdated(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                producer_version=self._producer_version,
                model_id=model.model_id,
                scan_id=scan_id,
                version=version,
                schema_version=CONTEXT_MODEL_SCHEMA,
                summary={"languages": len(model.identity.languages)},
            )
            await self._outbox.enqueue(completed_event)
            await self._outbox.enqueue(updated_event)
            await self._publisher.publish("context.scan.completed", completed_event)
            await self._publisher.publish("context.model.updated", updated_event)
            return model
        except Exception as exc:
            logger.exception("scan_failed", scan_id=str(scan_id))
            await self._repo.update_scan_status(
                scan_id,
                status="failed",
                error_code="SCAN_EXECUTION_ERROR",
                error_message=str(exc),
                completed_at=_utcnow(),
            )
            failed_event = ContextScanFailed(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                producer_version=self._producer_version,
                scan_id=scan_id,
                error_code="SCAN_EXECUTION_ERROR",
                error_message=str(exc),
                retryable=True,
            )
            await self._outbox.enqueue(failed_event)
            await self._publisher.publish("context.scan.failed", failed_event)
            raise


async def request_scan(
    repo: ContextRepository,
    outbox: OutboxWriter,
    publisher: EventPublisher,
    *,
    tenant_id: str,
    source: ScanSource,
    requested_by: str,
    idempotency_key: str,
    correlation_id: str,
    webhook_url: str | None = None,
    producer_version: str = AGENT_VERSION,
) -> dict[str, Any]:
    existing = await repo.get_scan_by_idempotency_key(tenant_id, idempotency_key)
    if existing:
        return existing

    scan_id = uuid4()
    record = await repo.create_scan(
        scan_id=scan_id,
        tenant_id=tenant_id,
        source=source,
        idempotency_key=idempotency_key,
        requested_by=requested_by,
        webhook_url=webhook_url,
        correlation_id=correlation_id,
    )
    requested = ContextScanRequested(
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        producer_version=producer_version,
        scan_id=scan_id,
        source=source,
        idempotency_key=idempotency_key,
        requested_by=requested_by,
        webhook_url=webhook_url,
    )
    await outbox.enqueue(requested)
    await publisher.publish("context.scan.requested", requested)
    return record
