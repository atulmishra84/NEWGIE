from __future__ import annotations
from uuid import UUID
from policy_intelligence.application.errors import NotFoundError
from policy_intelligence.domain.ports import DecisionRepository


class ExplainPolicyHandler:
    def __init__(self, decisions: DecisionRepository) -> None:
        self._decisions = decisions

    async def handle(self, decision_id: UUID, guardrail_id: str | None = None) -> dict:
        decision = await self._decisions.get(decision_id)
        if not decision:
            raise NotFoundError(f"Decision not found: {decision_id}")
        if guardrail_id:
            rec = next(
                (r for r in decision.recommendations if r.guardrail_id == guardrail_id),
                None,
            )
            if not rec:
                raise NotFoundError(f"Guardrail not in decision: {guardrail_id}")
            return {
                "decision_id": str(decision.decision_id),
                "guardrail": rec,
                "reasoning_path": [
                    s
                    for s in decision.reasoning_path
                    if guardrail_id in s.detail or guardrail_id in s.inputs
                ],
                "confidence": rec.confidence,
            }
        return {
            "decision_id": str(decision.decision_id),
            "summary": decision.summary,
            "recommendations": decision.recommendations,
            "reasoning_path": decision.reasoning_path,
            "confidence": decision.confidence,
        }
