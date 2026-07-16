"""Merge scanner findings by name keeping max confidence."""

from __future__ import annotations

from context_intelligence.domain.findings import DetectionFinding, merge_findings


def merge_by_name(findings: list[DetectionFinding]) -> list[DetectionFinding]:
    """Merge findings with the same section, category, and name (max confidence wins)."""
    buckets: dict[tuple[str, str, str], DetectionFinding] = {}
    for finding in findings:
        key = (finding.section.value, finding.category.value, finding.name)
        existing = buckets.get(key)
        if existing is None:
            buckets[key] = finding
            continue
        winner = finding if finding.confidence >= existing.confidence else existing
        loser = existing if winner is finding else finding
        merged_attrs = {**loser.attributes, **winner.attributes}
        merged_evidence = list(winner.evidence)
        seen_ids = {e.evidence_id for e in winner.evidence}
        for ref in loser.evidence:
            if ref.evidence_id not in seen_ids:
                merged_evidence.append(ref)
        buckets[key] = DetectionFinding(
            detector_id=winner.detector_id,
            section=winner.section,
            category=winner.category,
            name=winner.name,
            version=winner.version or loser.version,
            confidence=max(winner.confidence, loser.confidence),
            rationale=winner.rationale or loser.rationale,
            evidence=merged_evidence,
            attributes=merged_attrs,
            severity=winner.severity or loser.severity,
            fingerprint=winner.fingerprint or loser.fingerprint,
            location=winner.location or loser.location,
            graph_node=winner.graph_node or loser.graph_node,
            graph_edge=winner.graph_edge or loser.graph_edge,
        )
    return list(buckets.values())


def merge_scan_findings(findings: list[DetectionFinding]) -> list[DetectionFinding]:
    """Primary merge: by merge_key (name+version), then by name for leftovers."""
    primary = merge_findings(findings)
    return merge_by_name(primary)
