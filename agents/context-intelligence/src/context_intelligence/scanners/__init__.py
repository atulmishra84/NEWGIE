"""Production scanners: source readers, detectors, workspace materialization."""

from __future__ import annotations

from context_intelligence.scanners.registry import (
    DEFAULT_DETECTOR_REGISTRY,
    DEFAULT_READER_REGISTRY,
    DetectorRegistry,
    SourceReaderRegistry,
)
from context_intelligence.scanners.sources.base import SourceReader
from context_intelligence.scanners.detectors.base import BaseDetector
from context_intelligence.scanners.workspace import MaterializedWorkspace


def _import_readers() -> None:
    import context_intelligence.scanners.sources.folder_reader  # noqa: F401
    import context_intelligence.scanners.sources.git_reader  # noqa: F401
    import context_intelligence.scanners.sources.zip_reader  # noqa: F401
    import context_intelligence.scanners.sources.github_reader  # noqa: F401
    import context_intelligence.scanners.sources.container_reader  # noqa: F401
    import context_intelligence.scanners.sources.process_reader  # noqa: F401
    import context_intelligence.scanners.sources.kubernetes_reader  # noqa: F401
    import context_intelligence.scanners.sources.cloud_readers  # noqa: F401
    import context_intelligence.scanners.sources.ide_readers  # noqa: F401


def _import_detectors() -> None:
    import context_intelligence.scanners.detectors.language_detector  # noqa: F401
    import context_intelligence.scanners.detectors.package_manager_detector  # noqa: F401
    import context_intelligence.scanners.detectors.runtime_detector  # noqa: F401
    import context_intelligence.scanners.detectors.ai_framework_detector  # noqa: F401
    import context_intelligence.scanners.detectors.model_detector  # noqa: F401
    import context_intelligence.scanners.detectors.prompt_detector  # noqa: F401
    import context_intelligence.scanners.detectors.mcp_detector  # noqa: F401
    import context_intelligence.scanners.detectors.api_detector  # noqa: F401
    import context_intelligence.scanners.detectors.tool_detector  # noqa: F401
    import context_intelligence.scanners.detectors.vector_db_detector  # noqa: F401
    import context_intelligence.scanners.detectors.secrets_detector  # noqa: F401
    import context_intelligence.scanners.detectors.identity_detector  # noqa: F401
    import context_intelligence.scanners.detectors.deployment_detector  # noqa: F401
    import context_intelligence.scanners.detectors.memory_workflow_autonomy_detector  # noqa: F401


def build_default_readers() -> SourceReaderRegistry:
    """Return registry with all built-in source readers registered."""
    _import_readers()
    return DEFAULT_READER_REGISTRY


def build_default_detectors() -> DetectorRegistry:
    """Return registry with all built-in detectors registered."""
    _import_detectors()
    return DEFAULT_DETECTOR_REGISTRY


__all__ = [
    "MaterializedWorkspace",
    "SourceReader",
    "BaseDetector",
    "SourceReaderRegistry",
    "DetectorRegistry",
    "build_default_readers",
    "build_default_detectors",
]
