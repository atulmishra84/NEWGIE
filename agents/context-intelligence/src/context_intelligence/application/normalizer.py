"""Map merged detector findings into a normalized ContextModel."""

from __future__ import annotations

from collections.abc import Sequence

from gie_contracts.context_model import (
    AiSection,
    Confidence,
    ContextModel,
    DataSection,
    DeploymentSection,
    DetectedItem,
    EvidenceRef,
    GraphSection,
    IdentitySection,
    InterfacesSection,
    ProvenanceSection,
    ReasoningStep,
    SecretFinding,
    SecuritySection,
    Severity,
)
from gie_observability.context import get_context

from context_intelligence.domain.entities import ContextScan
from context_intelligence.domain.findings import (
    DetectionFinding,
    FindingCategory,
    FindingSection,
)


class ContextModelNormalizer:
    """Transforms merged findings into gie.context.v1."""

    def normalize(
        self,
        findings: Sequence[DetectionFinding],
        scan: ContextScan,
        source_digest: str | None,
        *,
        agent_version: str,
    ) -> ContextModel:
        identity = IdentitySection()
        ai = AiSection()
        interfaces = InterfacesSection()
        data = DataSection()
        security = SecuritySection()
        deployment = DeploymentSection()
        graph = GraphSection()
        detector_ids: set[str] = set()
        evidence_refs: list[EvidenceRef] = []
        reasoning_steps: list[ReasoningStep] = []

        for finding in findings:
            detector_ids.add(finding.detector_id)
            evidence_refs.extend(finding.evidence)
            self._apply_finding(
                finding,
                identity=identity,
                ai=ai,
                interfaces=interfaces,
                data=data,
                security=security,
                deployment=deployment,
                graph=graph,
            )

        ctx = get_context()
        if ctx is not None:
            for step in ctx.reasoning_path:
                reasoning_steps.append(
                    ReasoningStep(
                        step=step["step"],
                        detector_id=step["detector_id"],
                        action=step["action"],
                        detail=step["detail"],
                        confidence=Confidence(score=step["confidence"]["score"]),
                    )
                )

        confidence_score = self._aggregate_confidence(findings)
        provenance = ProvenanceSection(
            agent_version=agent_version,
            scan_id=scan.scan_id,
            tenant_id=scan.tenant_id,
            detectors=sorted(detector_ids),
            evidence=_dedupe_evidence(evidence_refs),
            confidence=Confidence(score=confidence_score),
            reasoning_path=reasoning_steps,
            source_type=scan.source.type.value,
            source_digest=source_digest,
        )

        return ContextModel(
            identity=identity,
            ai=ai,
            interfaces=interfaces,
            data=data,
            security=security,
            deployment=deployment,
            graph=graph,
            provenance=provenance,
        )

    def _apply_finding(
        self,
        finding: DetectionFinding,
        *,
        identity: IdentitySection,
        ai: AiSection,
        interfaces: InterfacesSection,
        data: DataSection,
        security: SecuritySection,
        deployment: DeploymentSection,
        graph: GraphSection,
    ) -> None:
        if finding.section == FindingSection.GRAPH:
            if finding.graph_node is not None:
                graph.nodes.append(finding.graph_node)
            if finding.graph_edge is not None:
                graph.edges.append(finding.graph_edge)
            return

        if finding.category == FindingCategory.SECRET:
            data.secret_findings.append(
                SecretFinding(
                    kind=finding.name,
                    location=finding.location or "unknown",
                    fingerprint=finding.fingerprint or finding.name,
                    severity=finding.severity or Severity.HIGH,
                    confidence=Confidence(
                        score=finding.confidence, rationale=finding.rationale
                    ),
                    evidence=finding.evidence,
                )
            )
            return

        if finding.category == FindingCategory.REGION:
            if finding.name not in identity.regions:
                identity.regions.append(finding.name)
            return

        if finding.category == FindingCategory.PROJECT_META:
            if finding.name == "project_name":
                identity.project_name = (
                    finding.attributes.get("value") or finding.version
                )
            elif finding.name == "repository_url":
                identity.repository_url = (
                    finding.attributes.get("value") or finding.version
                )
            return

        if finding.category == FindingCategory.ARCHITECTURE_NOTE:
            note = finding.rationale or finding.name
            if note not in deployment.architecture_notes:
                deployment.architecture_notes.append(note)
            return

        item = DetectedItem(
            name=finding.name,
            version=finding.version,
            confidence=Confidence(
                score=finding.confidence, rationale=finding.rationale
            ),
            evidence=finding.evidence,
            attributes=finding.attributes,
        )

        target = self._resolve_list(
            finding.category, identity, ai, interfaces, data, security, deployment
        )
        if target is not None:
            target.append(item)

    def _resolve_list(
        self,
        category: FindingCategory,
        identity: IdentitySection,
        ai: AiSection,
        interfaces: InterfacesSection,
        data: DataSection,
        security: SecuritySection,
        deployment: DeploymentSection,
    ) -> list[DetectedItem] | None:
        mapping: dict[FindingCategory, list[DetectedItem]] = {
            FindingCategory.LANGUAGE: identity.languages,
            FindingCategory.PACKAGE_MANAGER: identity.package_managers,
            FindingCategory.RUNTIME: identity.runtimes,
            FindingCategory.CLOUD_PROVIDER: identity.cloud_providers,
            FindingCategory.FRAMEWORK: ai.frameworks,
            FindingCategory.SDK: ai.sdks,
            FindingCategory.MODEL: ai.models,
            FindingCategory.PROMPT: ai.prompts,
            FindingCategory.MEMORY: ai.memory_architectures,
            FindingCategory.WORKFLOW: ai.workflows,
            FindingCategory.AUTONOMOUS: ai.autonomous_capabilities,
            FindingCategory.API: interfaces.apis,
            FindingCategory.TOOL: interfaces.tools,
            FindingCategory.MCP_SERVER: interfaces.mcp_servers,
            FindingCategory.WEBHOOK: interfaces.webhooks,
            FindingCategory.VECTOR_DATABASE: data.vector_databases,
            FindingCategory.DATA_STORE: data.data_stores,
            FindingCategory.IDENTITY_PROVIDER: security.identity_providers,
            FindingCategory.AUTH_SCHEME: security.auth_schemes,
            FindingCategory.SECRET_MANAGER: security.secret_managers,
            FindingCategory.CONTAINER: deployment.containers,
            FindingCategory.KUBERNETES: deployment.kubernetes,
            FindingCategory.CLOUD_RESOURCE: deployment.cloud_resources,
            FindingCategory.IDE_WORKSPACE: deployment.ide_workspaces,
        }
        return mapping.get(category)

    @staticmethod
    def _aggregate_confidence(findings: Sequence[DetectionFinding]) -> float:
        if not findings:
            return 0.0
        return sum(f.confidence for f in findings) / len(findings)


def _dedupe_evidence(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    seen: set[str] = set()
    unique: list[EvidenceRef] = []
    for ref in refs:
        if ref.evidence_id in seen:
            continue
        seen.add(ref.evidence_id)
        unique.append(ref)
    return unique
