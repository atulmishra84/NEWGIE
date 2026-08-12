"""Normalize heterogeneous learning inputs into FeedbackEvent list."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from gie_contracts.learning import FeedbackEvent, FeedbackType, LearningInputBundle


def _as_events(
    items: list[dict[str, Any]],
    feedback_type: FeedbackType,
    tenant_id: str,
    agent_id: str | None,
) -> list[FeedbackEvent]:
    out: list[FeedbackEvent] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            FeedbackEvent(
                feedback_id=str(
                    item.get("id") or item.get("feedback_id") or uuid4().hex[:16]
                ),
                tenant_id=tenant_id,
                agent_id=agent_id or item.get("agent_id"),
                feedback_type=feedback_type,
                title=str(item.get("title") or item.get("name") or feedback_type.value),
                description=str(
                    item.get("description")
                    or item.get("detail")
                    or item.get("summary")
                    or ""
                ),
                severity=str(item.get("severity") or "medium"),
                recommendation_id=item.get("recommendation_id"),
                policy_id=item.get("policy_id"),
                signals=dict(item.get("signals") or item),
                source=item.get("source"),
            )
        )
    return out


def collect_feedback(bundle: LearningInputBundle) -> list[FeedbackEvent]:
    events = list(bundle.feedback or [])
    tenant = bundle.tenant_id
    agent = bundle.agent_id
    events.extend(
        _as_events(
            bundle.runtime_telemetry, FeedbackType.RUNTIME_TELEMETRY, tenant, agent
        )
    )
    events.extend(
        _as_events(
            bundle.security_incidents, FeedbackType.SECURITY_INCIDENT, tenant, agent
        )
    )
    events.extend(
        _as_events(bundle.false_positives, FeedbackType.FALSE_POSITIVE, tenant, agent)
    )
    events.extend(
        _as_events(bundle.false_negatives, FeedbackType.FALSE_NEGATIVE, tenant, agent)
    )
    events.extend(
        _as_events(bundle.user_feedback, FeedbackType.USER_FEEDBACK, tenant, agent)
    )
    events.extend(
        _as_events(
            bundle.threat_intelligence, FeedbackType.THREAT_INTELLIGENCE, tenant, agent
        )
    )
    events.extend(
        _as_events(
            bundle.regulatory_updates, FeedbackType.REGULATORY_UPDATE, tenant, agent
        )
    )
    events.extend(
        _as_events(bundle.policy_changes, FeedbackType.POLICY_CHANGE, tenant, agent)
    )
    events.extend(
        _as_events(bundle.model_changes, FeedbackType.MODEL_CHANGE, tenant, agent)
    )
    # de-dupe by feedback_id
    seen: set[str] = set()
    unique: list[FeedbackEvent] = []
    for e in events:
        if e.feedback_id in seen:
            continue
        seen.add(e.feedback_id)
        unique.append(e)
    return unique
