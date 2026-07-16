"""Detector protocol and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gie_contracts.context_model import ContextModel


@dataclass
class DetectorResult:
    partial: ContextModel
    detector_id: str
    error: str | None = None


class Detector(ABC):
    detector_id: str

    @abstractmethod
    def detect(self, root: Path, *, tenant_id: str, scan_id: str) -> DetectorResult:
        raise NotImplementedError


class DetectorRegistry:
    def __init__(self) -> None:
        self._detectors: list[Detector] = []

    def register(self, detector: Detector) -> None:
        self._detectors.append(detector)

    def all(self) -> list[Detector]:
        return list(self._detectors)

    def run_all(self, root: Path, *, tenant_id: str, scan_id: str) -> list[DetectorResult]:
        results: list[DetectorResult] = []
        for detector in self._detectors:
            try:
                results.append(detector.detect(root, tenant_id=tenant_id, scan_id=scan_id))
            except Exception as exc:  # noqa: BLE001 — isolated per detector
                results.append(
                    DetectorResult(
                        partial=_empty_partial(tenant_id, scan_id),
                        detector_id=detector.detector_id,
                        error=str(exc),
                    )
                )
        return results


def _empty_partial(tenant_id: str, scan_id: str) -> ContextModel:
    from uuid import UUID

    from gie_contracts.context_model import ProvenanceSection

    return ContextModel(
        provenance=ProvenanceSection(
            agent_version="1.0.0",
            scan_id=UUID(scan_id) if len(scan_id) == 36 else UUID(int=0),
            tenant_id=tenant_id,
            source_type="folder",
        )
    )
