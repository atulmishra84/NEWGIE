"""Detector output normalized before Context Model assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from gie_contracts.context_model import EvidenceRef, GraphEdge, GraphNode, Severity


class FindingSection(StrEnum):
    IDENTITY = "identity"
    AI = "ai"
    INTERFACES = "interfaces"
    DATA = "data"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    GRAPH = "graph"
    PROVENANCE = "provenance"


class FindingCategory(StrEnum):
    LANGUAGE = "language"
    PACKAGE_MANAGER = "package_manager"
    RUNTIME = "runtime"
    CLOUD_PROVIDER = "cloud_provider"
    FRAMEWORK = "framework"
    SDK = "sdk"
    MODEL = "model"
    PROMPT = "prompt"
    MEMORY = "memory_architecture"
    WORKFLOW = "workflow"
    AUTONOMOUS = "autonomous_capability"
    API = "api"
    TOOL = "tool"
    MCP_SERVER = "mcp_server"
    WEBHOOK = "webhook"
    VECTOR_DATABASE = "vector_database"
    DATA_STORE = "data_store"
    SECRET = "secret"
    IDENTITY_PROVIDER = "identity_provider"
    AUTH_SCHEME = "auth_scheme"
    SECRET_MANAGER = "secret_manager"
    CONTAINER = "container"
    KUBERNETES = "kubernetes"
    CLOUD_RESOURCE = "cloud_resource"
    IDE_WORKSPACE = "ide_workspace"
    GRAPH_NODE = "graph_node"
    GRAPH_EDGE = "graph_edge"
    REGION = "region"
    PROJECT_META = "project_meta"
    ARCHITECTURE_NOTE = "architecture_note"


@dataclass(slots=True)
class DetectionFinding:
    """Single detector observation mapped into a Context Model section."""

    detector_id: str
    section: FindingSection
    category: FindingCategory
    name: str
    version: str | None = None
    confidence: float = 0.0
    rationale: str | None = None
    evidence: list[EvidenceRef] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    severity: Severity | None = None
    fingerprint: str | None = None
    location: str | None = None
    graph_node: GraphNode | None = None
    graph_edge: GraphEdge | None = None

    def merge_key(self) -> tuple[str, str, str, str | None]:
        return (self.section.value, self.category.value, self.name, self.version)

    def merged_into(self, other: DetectionFinding) -> DetectionFinding:
        """Combine duplicate findings by keeping higher confidence and union evidence."""
        if self.merge_key() != other.merge_key():
            raise ValueError("Cannot merge findings with different merge keys")
        winner, loser = (self, other) if self.confidence >= other.confidence else (other, self)
        evidence_ids = {e.evidence_id for e in winner.evidence}
        merged_evidence = list(winner.evidence)
        for ref in loser.evidence:
            if ref.evidence_id not in evidence_ids:
                merged_evidence.append(ref)
        merged_attrs = {**loser.attributes, **winner.attributes}
        return DetectionFinding(
            detector_id=winner.detector_id,
            section=winner.section,
            category=winner.category,
            name=winner.name,
            version=winner.version,
            confidence=winner.confidence,
            rationale=winner.rationale or loser.rationale,
            evidence=merged_evidence,
            attributes=merged_attrs,
            severity=winner.severity or loser.severity,
            fingerprint=winner.fingerprint or loser.fingerprint,
            location=winner.location or loser.location,
            graph_node=winner.graph_node or loser.graph_node,
            graph_edge=winner.graph_edge or loser.graph_edge,
        )


def merge_findings(findings: list[DetectionFinding]) -> list[DetectionFinding]:
    """Deduplicate and merge findings that target the same detected item."""
    merged: dict[tuple[str, str, str, str | None], DetectionFinding] = {}
    for finding in findings:
        key = finding.merge_key()
        if key in merged:
            merged[key] = merged[key].merged_into(finding)
        else:
            merged[key] = finding
    return list(merged.values())
