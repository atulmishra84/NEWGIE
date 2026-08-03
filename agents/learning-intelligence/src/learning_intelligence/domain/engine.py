"""Learning cycle: improve recommendations, detect drift, propose knowledge changes."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from gie_contracts.learning import (
    Confidence,
    DriftFinding,
    DriftSeverity,
    FeedbackEvent,
    FeedbackType,
    ImprovedRecommendation,
    KnowledgeChange,
    KnowledgeChangeStatus,
    LearningInputBundle,
    LearningReport,
    PolicyUpdateRecommendation,
)

from learning_intelligence.domain.ingest import collect_feedback
from learning_intelligence.version import AGENT_VERSION


def _sev(s: str) -> DriftSeverity:
    m = s.lower()
    if m in {"critical", "p0"}:
        return DriftSeverity.CRITICAL
    if m in {"high", "p1"}:
        return DriftSeverity.HIGH
    if m in {"low", "p3"}:
        return DriftSeverity.LOW
    return DriftSeverity.MEDIUM


def _conf_bump(base: float, events: list[FeedbackEvent]) -> tuple[float, float, list[str]]:
    score = base
    changes: list[str] = []
    for e in events:
        if e.feedback_type == FeedbackType.FALSE_POSITIVE:
            score = max(0.35, score - 0.08)
            changes.append(f"Lowered confidence due to FP: {e.title}")
        elif e.feedback_type == FeedbackType.FALSE_NEGATIVE:
            score = min(0.98, score + 0.05)
            changes.append(f"Raised urgency/confidence due to FN: {e.title}")
        elif e.feedback_type == FeedbackType.SECURITY_INCIDENT:
            score = min(0.98, score + 0.1)
            changes.append(f"Incident reinforces recommendation: {e.title}")
        elif e.feedback_type == FeedbackType.USER_FEEDBACK:
            sentiment = str(e.signals.get("sentiment") or e.signals.get("rating") or "").lower()
            if sentiment in {"negative", "bad", "1", "2"}:
                score = max(0.4, score - 0.05)
                changes.append(f"User negative feedback: {e.title}")
            else:
                score = min(0.97, score + 0.03)
                changes.append(f"User positive/neutral feedback: {e.title}")
        elif e.feedback_type == FeedbackType.RUNTIME_TELEMETRY:
            rate = float(e.signals.get("block_rate") or e.signals.get("trigger_rate") or 0)
            if rate > 0.3:
                score = max(0.4, score - 0.06)
                changes.append(f"High trigger rate suggests tuning: {e.title}")
            elif rate > 0:
                score = min(0.96, score + 0.02)
                changes.append(f"Telemetry supports control efficacy: {e.title}")
    delta = round(score - base, 3)
    return round(score, 3), delta, changes


def improve_recommendations(bundle: LearningInputBundle, events: list[FeedbackEvent]) -> tuple[list[ImprovedRecommendation], list[dict[str, Any]]]:
    improved: list[ImprovedRecommendation] = []
    conf_imps: list[dict[str, Any]] = []
    recs = list(bundle.current_recommendations or [])
    if not recs:
        # synthesize from FN / incidents
        for e in events:
            if e.feedback_type in {FeedbackType.FALSE_NEGATIVE, FeedbackType.SECURITY_INCIDENT, FeedbackType.THREAT_INTELLIGENCE}:
                recs.append(
                    {
                        "recommendation_id": e.recommendation_id or f"rec-learned-{uuid4().hex[:6]}",
                        "title": f"Address {e.title}",
                        "reason": e.description or e.title,
                        "priority": "high" if e.feedback_type != FeedbackType.THREAT_INTELLIGENCE else "medium",
                        "category": "security",
                        "confidence": {"score": 0.7},
                    }
                )
    for rec in recs:
        rid = str(rec.get("recommendation_id") or uuid4().hex[:12])
        related = [e for e in events if e.recommendation_id == rid or _relates(e, rec)]
        prev = float((rec.get("confidence") or {}).get("score") if isinstance(rec.get("confidence"), dict) else rec.get("confidence") or 0.75)
        new_score, delta, changes = _conf_bump(prev, related or events[:3])
        # priority bump on incidents/FN
        priority = str(rec.get("priority") or "medium")
        if any(e.feedback_type in {FeedbackType.SECURITY_INCIDENT, FeedbackType.FALSE_NEGATIVE} for e in related):
            if priority in {"low", "medium"}:
                priority = "high"
                changes.append("Priority elevated due to incident/FN signal")
        item = ImprovedRecommendation(
            recommendation_id=rid,
            title=str(rec.get("title") or "Recommendation"),
            reason=str(rec.get("reason") or "Updated from learning signals"),
            previous_confidence=prev,
            confidence=Confidence(score=new_score, previous_score=prev, delta=delta, rationale="; ".join(changes[:4]) or "stable"),
            priority=priority,
            category=str(rec.get("category") or "security"),
            changes=changes,
            related_feedback_ids=[e.feedback_id for e in related],
        )
        improved.append(item)
        if delta:
            conf_imps.append({"recommendation_id": rid, "previous": prev, "new": new_score, "delta": delta})
    return improved, conf_imps


def _relates(event: FeedbackEvent, rec: dict[str, Any]) -> bool:
    hay = " ".join(
        [
            str(rec.get("title") or ""),
            str(rec.get("category") or ""),
            " ".join(str(x) for x in rec.get("related_guardrails") or []),
            str(event.title),
            str(event.description),
            str(event.signals),
        ]
    ).lower()
    keys = ["prompt", "pii", "tool", "injection", "identity", "rate", "model", "policy"]
    return any(k in hay and k in str(event.title + event.description).lower() for k in keys) or event.feedback_type in {
        FeedbackType.REGULATORY_UPDATE,
        FeedbackType.THREAT_INTELLIGENCE,
        FeedbackType.MODEL_CHANGE,
        FeedbackType.POLICY_CHANGE,
    }


def detect_drift(events: list[FeedbackEvent], bundle: LearningInputBundle) -> list[DriftFinding]:
    findings: list[DriftFinding] = []
    for e in events:
        if e.feedback_type == FeedbackType.POLICY_CHANGE:
            findings.append(
                DriftFinding(
                    kind="policy_drift",
                    title=f"Policy change observed: {e.title}",
                    detail=e.description or "Policy inventory changed relative to last recommendation cycle",
                    severity=_sev(e.severity),
                    evidence=[e.feedback_id, e.source or "policy_change"],
                )
            )
        if e.feedback_type == FeedbackType.REGULATORY_UPDATE:
            findings.append(
                DriftFinding(
                    kind="regulation_change",
                    title=f"Regulatory update: {e.title}",
                    detail=e.description or "New or updated regulation may invalidate prior mappings",
                    severity=_sev(e.severity) if e.severity != "medium" else DriftSeverity.HIGH,
                    evidence=[e.feedback_id, str(e.signals.get("framework") or "regulation")],
                )
            )
        if e.feedback_type == FeedbackType.THREAT_INTELLIGENCE:
            findings.append(
                DriftFinding(
                    kind="new_attack_technique",
                    title=f"New attack technique: {e.title}",
                    detail=e.description or "Threat intel indicates technique not covered by current controls",
                    severity=_sev(e.severity) if e.severity != "medium" else DriftSeverity.HIGH,
                    evidence=[e.feedback_id, str(e.signals.get("technique_id") or e.signals.get("atlas_id") or "threat")],
                )
            )
        if e.feedback_type == FeedbackType.MODEL_CHANGE:
            findings.append(
                DriftFinding(
                    kind="policy_drift",
                    title=f"Model change may invalidate policies: {e.title}",
                    detail=e.description or "Model swap/version change can alter guardrail efficacy",
                    severity=DriftSeverity.MEDIUM,
                    evidence=[e.feedback_id],
                )
            )
        if e.feedback_type == FeedbackType.RUNTIME_TELEMETRY:
            block_rate = float(e.signals.get("block_rate") or 0)
            if block_rate > 0.25:
                findings.append(
                    DriftFinding(
                        kind="policy_drift",
                        title=f"Possible over-blocking drift: {e.title}",
                        detail=f"block_rate={block_rate}",
                        severity=DriftSeverity.MEDIUM,
                        evidence=[e.feedback_id, f"block_rate={block_rate}"],
                    )
                )
    # baseline compare with current policies fingerprint
    if bundle.current_policies and bundle.knowledge_snapshot.get("policy_fingerprint"):
        if str(bundle.current_policies.get("version")) != str(bundle.knowledge_snapshot.get("policy_version")):
            findings.append(
                DriftFinding(
                    kind="policy_drift",
                    title="Policy version drift vs knowledge snapshot",
                    detail=f"current={bundle.current_policies.get('version')} snapshot={bundle.knowledge_snapshot.get('policy_version')}",
                    severity=DriftSeverity.MEDIUM,
                    evidence=["policy_version_mismatch"],
                )
            )
    return findings


def recommend_policy_updates(drift: list[DriftFinding], events: list[FeedbackEvent], improved: list[ImprovedRecommendation]) -> list[PolicyUpdateRecommendation]:
    updates: list[PolicyUpdateRecommendation] = []
    for d in drift:
        if d.kind == "new_attack_technique":
            updates.append(
                PolicyUpdateRecommendation(
                    title=f"Add detection/control for {d.title}",
                    description=d.detail,
                    target_policy="prompt-policy.json / opa.rego",
                    rationale="Threat intelligence indicates coverage gap",
                    severity=d.severity,
                    suggested_diff={"add_rules": ["block_new_technique"], "evidence": d.evidence},
                )
            )
        if d.kind == "regulation_change":
            updates.append(
                PolicyUpdateRecommendation(
                    title=f"Update compliance mappings for {d.title}",
                    description=d.detail,
                    target_policy="guardrails.yaml",
                    rationale="Regulatory update requires control remapping",
                    severity=d.severity,
                    suggested_diff={"compliance_mapping_refresh": True, "evidence": d.evidence},
                )
            )
        if d.kind == "policy_drift" and "over-blocking" in d.title.lower():
            updates.append(
                PolicyUpdateRecommendation(
                    title="Tune thresholds to reduce false positives",
                    description=d.detail,
                    target_policy="openai-policy.json",
                    rationale="Runtime telemetry shows elevated block rate",
                    severity=d.severity,
                    suggested_diff={"adjust": {"injection_threshold": 0.8}},
                )
            )
    for e in events:
        if e.feedback_type == FeedbackType.FALSE_NEGATIVE:
            updates.append(
                PolicyUpdateRecommendation(
                    title=f"Close FN gap: {e.title}",
                    description=e.description or "Strengthen deny rules",
                    target_policy="opa.rego",
                    rationale="False negative reported in production",
                    severity=_sev(e.severity),
                    suggested_diff={"add_deny": e.signals.get("pattern") or e.title},
                )
            )
    # dedupe by title
    seen: set[str] = set()
    unique: list[PolicyUpdateRecommendation] = []
    for u in updates:
        if u.title in seen:
            continue
        seen.add(u.title)
        unique.append(u)
    return unique[:30]


def propose_knowledge_changes(
    *,
    tenant_id: str,
    events: list[FeedbackEvent],
    drift: list[DriftFinding],
    improved: list[ImprovedRecommendation],
    policy_updates: list[PolicyUpdateRecommendation],
    allow_auto_publish: bool = False,
) -> list[KnowledgeChange]:
    changes: list[KnowledgeChange] = []
    for d in drift:
        if d.kind == "new_attack_technique":
            changes.append(
                KnowledgeChange(
                    tenant_id=tenant_id,
                    title=d.title,
                    description=d.detail,
                    change_type="attack_technique",
                    payload={"drift": d.model_dump(mode="json")},
                    status=KnowledgeChangeStatus.PUBLISHED if allow_auto_publish else KnowledgeChangeStatus.PROPOSED,
                    requires_human_approval=not allow_auto_publish,
                    source_feedback_ids=list(d.evidence)[:10],
                    confidence=Confidence(score=0.82, rationale="Threat intel derived"),
                )
            )
        if d.kind == "regulation_change":
            changes.append(
                KnowledgeChange(
                    tenant_id=tenant_id,
                    title=d.title,
                    description=d.detail,
                    change_type="regulation",
                    payload={"drift": d.model_dump(mode="json")},
                    status=KnowledgeChangeStatus.PUBLISHED if allow_auto_publish else KnowledgeChangeStatus.PROPOSED,
                    requires_human_approval=not allow_auto_publish,
                    source_feedback_ids=list(d.evidence)[:10],
                    confidence=Confidence(score=0.88, rationale="Regulatory feed"),
                )
            )
    for u in policy_updates[:10]:
        changes.append(
            KnowledgeChange(
                tenant_id=tenant_id,
                title=u.title,
                description=u.description,
                change_type="policy_rule",
                payload=u.model_dump(mode="json"),
                status=KnowledgeChangeStatus.PROPOSED,
                requires_human_approval=True,
                source_feedback_ids=[],
                confidence=Confidence(score=0.8, rationale="Learning cycle proposal"),
            )
        )
    for rec in improved:
        if rec.confidence.delta and abs(rec.confidence.delta) >= 0.05:
            changes.append(
                KnowledgeChange(
                    tenant_id=tenant_id,
                    title=f"Updated recommendation confidence: {rec.title}",
                    description=rec.confidence.rationale or "Confidence adjusted",
                    change_type="recommendation",
                    payload=rec.model_dump(mode="json"),
                    status=KnowledgeChangeStatus.PROPOSED,
                    requires_human_approval=True,
                    source_feedback_ids=rec.related_feedback_ids,
                    confidence=rec.confidence,
                )
            )
    return changes


def run_learning_cycle(bundle: LearningInputBundle, *, allow_auto_publish: bool = False) -> LearningReport:
    events = collect_feedback(bundle)
    reasoning = [
        {"step": 1, "action": "ingest_feedback", "detail": f"Consumed {len(events)} feedback signals"},
    ]
    improved, conf_imps = improve_recommendations(bundle, events)
    reasoning.append({"step": 2, "action": "improve_recommendations", "detail": f"{len(improved)} recommendations updated"})
    drift = detect_drift(events, bundle)
    reasoning.append({"step": 3, "action": "detect_drift", "detail": f"{len(drift)} drift findings"})
    updates = recommend_policy_updates(drift, events, improved)
    reasoning.append({"step": 4, "action": "recommend_policy_updates", "detail": f"{len(updates)} policy updates"})
    # Never auto-publish unless explicitly allowed (settings + request flag)
    auto = bool(allow_auto_publish and bundle.publish_without_approval)
    knowledge = []
    if bundle.auto_propose_knowledge:
        knowledge = propose_knowledge_changes(
            tenant_id=bundle.tenant_id,
            events=events,
            drift=drift,
            improved=improved,
            policy_updates=updates,
            allow_auto_publish=auto,
        )
        reasoning.append(
            {
                "step": 5,
                "action": "propose_knowledge",
                "detail": f"{len(knowledge)} knowledge changes (human approval required={not auto})",
            }
        )
    counts = {
        "feedback": len(events),
        "improved_recommendations": len(improved),
        "policy_updates": len(updates),
        "drift_findings": len(drift),
        "knowledge_changes": len(knowledge),
        "knowledge_proposed": sum(1 for k in knowledge if k.status == KnowledgeChangeStatus.PROPOSED),
    }
    avg_conf = sum(r.confidence.score for r in improved) / len(improved) if improved else 0.7
    summary = (
        f"Learning cycle consumed {counts['feedback']} signals; "
        f"improved={counts['improved_recommendations']}, drift={counts['drift_findings']}, "
        f"policy_updates={counts['policy_updates']}, knowledge_proposed={counts['knowledge_proposed']}"
    )
    return LearningReport(
        tenant_id=bundle.tenant_id,
        agent_id=bundle.agent_id,
        agent_version=AGENT_VERSION,
        improved_recommendations=improved,
        policy_updates=updates,
        drift_findings=drift,
        knowledge_changes=knowledge,
        confidence_improvements=conf_imps,
        feedback_consumed=len(events),
        confidence=Confidence(score=round(avg_conf, 3), rationale="Aggregate improved recommendation confidence"),
        reasoning_path=reasoning,
        summary=summary,
        counts=counts,
    )
