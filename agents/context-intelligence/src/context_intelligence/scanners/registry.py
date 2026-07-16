"""Entry-point style registries for source readers and detectors."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import TypeVar

from gie_contracts.sources import ScanSource, SourceType

from context_intelligence.domain.findings import DetectionFinding
from context_intelligence.scanners.sources.base import SourceReader
from context_intelligence.scanners.detectors.base import BaseDetector

TReader = TypeVar("TReader", bound=SourceReader)
TDetector = TypeVar("TDetector", bound=BaseDetector)

ReaderFactory = Callable[[], SourceReader]
DetectorFactory = Callable[[], BaseDetector]


class SourceReaderRegistry:
    """Maps source types to reader implementations."""

    def __init__(self) -> None:
        self._factories: dict[SourceType, ReaderFactory] = {}
        self._instances: dict[SourceType, SourceReader] = {}

    def register(
        self,
        source_type: SourceType,
        factory: ReaderFactory | type[SourceReader],
    ) -> None:
        if isinstance(factory, type):
            cls = factory
            self._factories[source_type] = cls
            return
        self._factories[source_type] = factory

    def register_reader(
        self, *source_types: SourceType
    ) -> Callable[[type[TReader]], type[TReader]]:
        def decorator(cls: type[TReader]) -> type[TReader]:
            for source_type in source_types:
                self.register(source_type, cls)
            return cls

        return decorator

    def get(self, source_type: SourceType) -> SourceReader | None:
        if source_type in self._instances:
            return self._instances[source_type]
        factory = self._factories.get(source_type)
        if factory is None:
            return None
        if isinstance(factory, type):
            instance = factory()
        else:
            instance = factory()
        self._instances[source_type] = instance
        return instance

    def resolve(self, source: ScanSource) -> SourceReader:
        reader = self.get(source.type)
        if reader is None:
            raise KeyError(f"No source reader registered for {source.type.value}")
        return reader

    def supported_types(self) -> frozenset[SourceType]:
        return frozenset(self._factories)

    def all_readers(self) -> list[SourceReader]:
        return [self.get(st) for st in self._factories if self.get(st) is not None]  # type: ignore[misc]


class DetectorRegistry:
    """Registry of pluggable async detectors."""

    def __init__(self) -> None:
        self._factories: list[DetectorFactory] = []
        self._instances: list[BaseDetector] | None = None

    def register(self, factory: DetectorFactory | type[BaseDetector]) -> None:
        if isinstance(factory, type):
            self._factories.append(factory)
        else:
            self._factories.append(factory)

    def register_detector(self) -> Callable[[type[TDetector]], type[TDetector]]:
        def decorator(cls: type[TDetector]) -> type[TDetector]:
            self.register(cls)
            return cls

        return decorator

    def all(self) -> list[BaseDetector]:
        if self._instances is None:
            built: list[BaseDetector] = []
            for factory in self._factories:
                if isinstance(factory, type):
                    built.append(factory())
                else:
                    built.append(factory())
            self._instances = built
        return list(self._instances)

    async def run_all(self, workspace_path) -> list[DetectionFinding]:
        from pathlib import Path

        root = Path(workspace_path)
        findings: list[DetectionFinding] = []
        for detector in self.all():
            try:
                findings.extend(await detector.detect(root))
            except Exception as exc:  # noqa: BLE001 — isolate per detector
                findings.append(
                    DetectionFinding(
                        detector_id=detector.detector_id,
                        section=detector.section,
                        category=detector.default_category,
                        name="detector_error",
                        confidence=0.0,
                        rationale=str(exc),
                        attributes={"error": str(exc)},
                    )
                )
        return findings


DEFAULT_READER_REGISTRY = SourceReaderRegistry()
DEFAULT_DETECTOR_REGISTRY = DetectorRegistry()


def reader_registry() -> SourceReaderRegistry:
    return DEFAULT_READER_REGISTRY


def detector_registry() -> DetectorRegistry:
    return DEFAULT_DETECTOR_REGISTRY
