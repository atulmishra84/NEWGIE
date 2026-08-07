"""Policy Engine API — allow/deny deploy decisions."""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from gie_contracts import PolicyDecision, PolicyReport
from gie_llm import BedrockLLMClient
from policy_engine import __version__

app = FastAPI(title="GIE Policy Engine", version=__version__)

_llm: BedrockLLMClient | None = None


def _get_llm() -> BedrockLLMClient | None:
    global _llm
    if os.environ.get("BEDROCK_ENABLED", "true").lower() == "false":
        return None
    if _llm is None:
        _llm = BedrockLLMClient(
            region=os.environ.get("AWS_REGION", "us-east-1"),
            model_id=os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN", ""),
        )
    return _llm


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

    decision = PolicyDecision.DENY if deny_on else PolicyDecision.ALLOW
    report = PolicyReport(
        decision=decision,
        reasons=reasons or ["within_policy"],
        risk_score=body.risk_score,
        deny_on=deny_on,
    )

    llm = _get_llm()
    if llm:
        enhancement = await llm.enhance(
            agent_name="Policy Engine",
            deterministic_output={
                "decision": decision.value,
                "risk_score": body.risk_score,
                "risk_level": body.risk_level,
                "deny_reasons": deny_on,
            },
            context_summary=(
                "Explain the allow/deny policy decision for this AI deployment. "
                "Provide clear rationale and next steps."
            ),
        )
        if enhancement.get("narrative"):
            report = report.model_copy(update={"llm_enhancement": {
                "narrative": enhancement["narrative"],
                "key_insights": enhancement.get("key_insights", []),
                "recommendations": enhancement.get("recommendations", []),
                "model": llm._model_id,
            }})

    return report
