"""Folder scan application service."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from uuid import UUID, uuid4

from gie_contracts.context_model import Confidence, ContextModel, ProvenanceSection
from gie_contracts.sources import FolderSource

from context_intelligence.config import settings
from context_intelligence.domain.detectors.base import DetectorRegistry
from context_intelligence.domain.detectors.manifest import ManifestDetector
from context_intelligence.domain.merge import merge_context_models


def _build_registry() -> DetectorRegistry:
    registry = DetectorRegistry()
    registry.register(ManifestDetector())
    return registry


def _digest_root(root: Path) -> str:
    h = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if count >= settings.scan_max_files:
            break
        try:
            if path.stat().st_size > settings.scan_max_file_bytes:
                continue
            h.update(str(path.relative_to(root)).encode())
            h.update(path.read_bytes())
            count += 1
        except OSError:
            continue
    return f"sha256:{h.hexdigest()[:32]}"


def scan_folder(
    path: str | Path,
    *,
    tenant_id: str = "default",
    scan_id: UUID | None = None,
) -> ContextModel:
    root = Path(path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"scan path is not a directory: {root}")

    scan_uuid = scan_id or uuid4()
    started = time.perf_counter()
    registry = _build_registry()
    results = registry.run_all(root, tenant_id=tenant_id, scan_id=str(scan_uuid))

    base = ContextModel(
        provenance=ProvenanceSection(
            agent_version=settings.agent_version,
            scan_id=scan_uuid,
            tenant_id=tenant_id,
            source_type=FolderSource.model_fields["type"].default,
            source_digest=_digest_root(root),
            detectors=[],
            confidence=Confidence(score=0.0),
        )
    )

    partials = [r.partial for r in results if r.error is None]
    merged = merge_context_models(base, *partials) if partials else base
    merged.provenance.detectors = [r.detector_id for r in results]
    merged.provenance.confidence = Confidence(
        score=min(1.0, 0.5 + 0.1 * len([r for r in results if r.error is None])),
        rationale=f"completed in {(time.perf_counter() - started) * 1000:.0f}ms",
    )
    if root.name:
        merged.identity.project_name = root.name
    return merged
