"""Compliance applicability, gap analysis, scoring, audit package."""

from __future__ import annotations
import json
from typing import Any
from uuid import uuid4

from gie_contracts.compliance import (
    ComplianceGap,
    ComplianceInputBundle,
    ComplianceMatrixRow,
    ComplianceReport,
    Confidence,
    ControlAssessment,
    ControlStatus,
    EvidenceItem,
    FrameworkApplicability,
    FrameworkId,
    GapSeverity,
)

from compliance_intelligence.domain.catalog import load_catalog
from compliance_intelligence.version import AGENT_VERSION

# Recommended guardrail/control aliases when gaps found
REMEDIATION_MAP = {
    "hipaa-phi-min": ["gr-pii-presidio", "gr-output-filter"],
    "hipaa-access": ["gr-identity-rbac"],
    "hipaa-audit": ["gr-opa-runtime"],
    "gdpr-art32": ["gr-output-filter", "gr-pii-presidio"],
    "gdpr-art22": ["gr-tool-allowlist"],
    "gdpr-dpia": ["gr-eu-ai-transparency"],
    "pci-pan-mask": ["gr-pii-presidio", "gr-output-filter"],
    "soc2-cc6": ["gr-identity-rbac"],
    "soc2-cc7": ["gr-rate-limit"],
    "euai-transparency": ["gr-eu-ai-transparency"],
    "euai-human": ["gr-tool-allowlist"],
    "int-shadow": ["gr-topic-safety"],
    "dora-thirdparty": ["gr-opa-runtime"],
    "mas-feat": ["gr-output-filter"],
}


def _haystack(bundle: ComplianceInputBundle) -> str:
    return json.dumps(
        {
            "context": bundle.context_model,
            "risk": bundle.risk_report,
            "knowledge": bundle.knowledge,
            "identity": bundle.identity,
            "business": bundle.business,
            "internal": bundle.internal_policies,
        },
        default=str,
    ).lower()


def determine_applicability(
    bundle: ComplianceInputBundle,
) -> list[FrameworkApplicability]:
    cat = load_catalog()
    hay = _haystack(bundle)
    declared = {
        f.value if isinstance(f, FrameworkId) else str(f)
        for f in bundle.declared_frameworks
    }
    results: list[FrameworkApplicability] = []
    for fid, meta in cat["frameworks"].items():
        triggers = meta.get("triggers", [])
        matched = [t for t in triggers if t in hay]
        applicable = (
            bool(matched)
            or fid in declared
            or (fid == "internal_corporate" and bool(bundle.internal_policies))
        )
        # Always consider NIST AI RMF for any AI app
        if fid == "nist_ai_rmf" and (
            "ai" in hay or "llm" in hay or "agent" in hay or "openai" in hay
        ):
            applicable = True
            if "ai system" not in matched:
                matched.append("ai system baseline")
        reasons = []
        if fid in declared:
            reasons.append("Explicitly declared by requester")
        if matched:
            reasons.append(f"Matched signals: {', '.join(matched[:6])}")
        if applicable and not reasons:
            reasons.append("Baseline applicability heuristics")
        conf = min(0.98, 0.5 + 0.1 * len(matched) + (0.2 if fid in declared else 0))
        results.append(
            FrameworkApplicability(
                framework=FrameworkId(fid),
                applicable=applicable,
                confidence=Confidence(
                    score=round(conf, 3), rationale="trigger + declaration match"
                ),
                reasons=reasons or ["Not applicable based on current signals"],
                version=meta.get("version", "1.0.0"),
                last_regulatory_update=meta.get("last_update"),
            )
        )
    return results


def _status_for(
    control_id: str,
    implemented: set[str],
    evidence_by_control: dict[str, list[EvidenceItem]],
) -> ControlStatus:
    if control_id in implemented:
        return (
            ControlStatus.IMPLEMENTED
            if evidence_by_control.get(control_id)
            else ControlStatus.PARTIAL
        )
    if evidence_by_control.get(control_id):
        return ControlStatus.PARTIAL
    return ControlStatus.MISSING


def _severity(status: ControlStatus, category: str) -> GapSeverity | None:
    if status in {ControlStatus.IMPLEMENTED, ControlStatus.NOT_APPLICABLE}:
        return None
    if status == ControlStatus.MISSING:
        return (
            GapSeverity.CRITICAL
            if category in {"privacy", "access", "data", "security"}
            else GapSeverity.HIGH
        )
    return GapSeverity.MEDIUM


def analyze_compliance(bundle: ComplianceInputBundle) -> ComplianceReport:
    cat = load_catalog()
    applicable = determine_applicability(bundle)
    implemented = set(bundle.implemented_controls)
    evidence_by_control: dict[str, list[EvidenceItem]] = {}
    for ev in bundle.evidence:
        evidence_by_control.setdefault(ev.control_id, []).append(ev)

    assessments: list[ControlAssessment] = []
    gaps: list[ComplianceGap] = []
    matrix: list[ComplianceMatrixRow] = []
    mappings: dict[str, list[str]] = {}
    reasoning: list[dict[str, Any]] = [
        {
            "step": 1,
            "action": "load_catalog",
            "detail": f"Catalog version {cat.get('version')}",
        },
        {
            "step": 2,
            "action": "determine_applicability",
            "detail": f"Evaluated {len(applicable)} frameworks",
        },
    ]

    for fa in applicable:
        if not fa.applicable:
            continue
        meta = cat["frameworks"][fa.framework.value]
        for ctrl in meta.get("controls", []):
            cid = ctrl["id"]
            status = _status_for(cid, implemented, evidence_by_control)
            sev = _severity(status, ctrl.get("category", "general"))
            recs = REMEDIATION_MAP.get(cid, ["gr-output-filter", "gr-identity-rbac"])
            ev_list = evidence_by_control.get(cid, [])
            # Auto-generate synthetic evidence pointers for implemented controls without uploads
            if status == ControlStatus.IMPLEMENTED and not ev_list:
                ev_list = [
                    EvidenceItem(
                        control_id=cid,
                        title=f"Declared implementation: {ctrl['title']}",
                        description="Control marked implemented by requester; collect audit artifacts.",
                        source="declared",
                    )
                ]
            assessment = ControlAssessment(
                control_id=cid,
                framework=fa.framework,
                title=ctrl["title"],
                status=status,
                gap_severity=sev,
                gap_description=None
                if status == ControlStatus.IMPLEMENTED
                else f"Gap against {ctrl['title']}: {ctrl['description']}",
                recommended_controls=recs
                if status != ControlStatus.IMPLEMENTED
                else [],
                evidence=ev_list,
                confidence=Confidence(
                    score=0.9 if status == ControlStatus.IMPLEMENTED else 0.75
                ),
                mapping_refs=[f"{fa.framework.value}:{cid}"],
            )
            assessments.append(assessment)
            matrix.append(
                ComplianceMatrixRow(
                    framework=fa.framework,
                    control_id=cid,
                    title=ctrl["title"],
                    status=status,
                    evidence_count=len(ev_list),
                    gap_severity=sev,
                )
            )
            mappings.setdefault(fa.framework.value, []).append(cid)
            if status in {ControlStatus.MISSING, ControlStatus.PARTIAL} and sev:
                gaps.append(
                    ComplianceGap(
                        gap_id=uuid4().hex[:12],
                        framework=fa.framework,
                        control_id=cid,
                        title=ctrl["title"],
                        severity=sev,
                        description=assessment.gap_description or "",
                        recommended_controls=recs,
                    )
                )
            reasoning.append(
                {
                    "step": len(reasoning) + 1,
                    "action": "assess_control",
                    "detail": f"{cid} -> {status.value}",
                    "framework": fa.framework.value,
                }
            )

    # Score: implemented(+partial*0.5) / assessed
    if assessments:
        points = sum(
            1.0
            if a.status == ControlStatus.IMPLEMENTED
            else 0.5
            if a.status == ControlStatus.PARTIAL
            else 0.0
            for a in assessments
        )
        score = points / len(assessments)
    else:
        score = 0.0

    all_evidence = [e for a in assessments for e in a.evidence]
    policy_version = bundle.policy_version or cat.get("version", "1.0.0")
    audit_package = {
        "package_id": uuid4().hex,
        "policy_version": policy_version,
        "catalog_version": cat.get("version"),
        "application_id": bundle.application_id,
        "applicable_frameworks": [
            f.framework.value for f in applicable if f.applicable
        ],
        "compliance_score": round(score, 3),
        "gap_count": len(gaps),
        "evidence_count": len(all_evidence),
        "matrix_rows": len(matrix),
        "artifacts": [
            {"type": "compliance_matrix", "format": "json"},
            {"type": "gap_analysis", "format": "json"},
            {"type": "evidence_report", "format": "json"},
            {"type": "control_mapping", "format": "json"},
        ],
    }
    applicable_names = [f.framework.value for f in applicable if f.applicable]
    summary = (
        f"{len(applicable_names)} frameworks applicable; score={score:.0%}; "
        f"{len(gaps)} gaps; {len(all_evidence)} evidence items; policy={policy_version}"
    )
    return ComplianceReport(
        tenant_id=bundle.tenant_id,
        application_id=bundle.application_id,
        agent_version=AGENT_VERSION,
        applicable_frameworks=applicable,
        assessments=assessments,
        gaps=gaps,
        matrix=matrix,
        evidence=all_evidence,
        compliance_score=round(score, 3),
        confidence=Confidence(score=0.85, rationale="catalog-driven assessment"),
        policy_version=policy_version,
        audit_package=audit_package,
        control_mappings=mappings,
        reasoning_path=reasoning,
        summary=summary,
    )


def validate_controls(
    *,
    prior: ComplianceReport,
    implemented_controls: list[str],
    evidence: list[EvidenceItem],
    control_ids: list[str] | None = None,
) -> ComplianceReport:
    """Re-validate selected controls against new evidence/implementation claims."""
    implemented = set(prior.assessments and [])  # start empty then merge
    implemented = {
        a.control_id for a in prior.assessments if a.status == ControlStatus.IMPLEMENTED
    }
    implemented.update(implemented_controls)
    # Rebuild a minimal bundle-like reassess using prior matrix frameworks
    from gie_contracts.compliance import ComplianceInputBundle

    bundle = ComplianceInputBundle(
        tenant_id=prior.tenant_id,
        application_id=prior.application_id,
        declared_frameworks=[
            f.framework for f in prior.applicable_frameworks if f.applicable
        ],
        implemented_controls=list(implemented),
        evidence=list(prior.evidence) + list(evidence),
        policy_version=prior.policy_version,
        context_model={"revalidate": True},
    )
    report = analyze_compliance(bundle)
    if control_ids:
        wanted = set(control_ids)
        report.assessments = [
            a for a in report.assessments if a.control_id in wanted
        ] or report.assessments
    return report
