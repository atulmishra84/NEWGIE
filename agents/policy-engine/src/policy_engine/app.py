"""Policy Engine API — allow/deny deploy decisions."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from gie_contracts import PolicyDecision, PolicyReport
from policy_engine import __version__

app = FastAPI(title="GIE Policy Engine", version=__version__)


class EvaluateRequest(BaseModel):
    risk_score: float = 0.0
    risk_level: str = "low"
    force_deny: bool = False
    deny_threshold: float = Field(default=80.0, ge=0.0, le=100.0)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "agent": "policy-engine", "version": __version__}


@app.post("/v1/policy/evaluate", response_model=PolicyReport)
async def evaluate(body: EvaluateRequest) -> PolicyReport:
    deny_on: list[str] = []
    reasons: list[str] = []
    if body.force_deny:
        deny_on.append("force_deny")
        reasons.append("Explicit policy deny fixture")
    if body.risk_score >= body.deny_threshold:
        deny_on.append("risk_threshold")
        reasons.append(f"Risk score {body.risk_score} >= {body.deny_threshold}")
    if body.risk_level in {"critical", "high"} and body.risk_score >= 60:
        deny_on.append("risk_level")
        reasons.append(f"Risk level {body.risk_level}")

    if deny_on:
        return PolicyReport(
            decision=PolicyDecision.DENY,
            reasons=reasons or ["denied"],
            risk_score=body.risk_score,
            deny_on=deny_on,
        )
    return PolicyReport(
        decision=PolicyDecision.ALLOW,
        reasons=["within_policy"],
        risk_score=body.risk_score,
        deny_on=[],
    )
