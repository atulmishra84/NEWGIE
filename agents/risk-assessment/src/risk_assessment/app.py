"""Risk Assessment API."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from gie_contracts import RiskReport, Severity
from gie_llm import BedrockLLMClient
from risk_assessment import __version__

app = FastAPI(title="GIE Risk Assessment", version=__version__)

_llm: BedrockLLMClient | None = None


def _get_llm() -> BedrockLLMClient | None:
    global _llm
    if os.environ.get("BEDROCK_ENABLED", "true").lower() == "false":
        return None
    if _llm is None:
        _llm = BedrockLLMClient(
            region=os.environ.get("AWS_REGION", "us-east-1"),
            model_id=os.environ.get(
                "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
            ),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN", ""),
        )
    return _llm


class AssessRequest(BaseModel):
    context_model_id: str
    blocking_findings: int = 0
    force_high: bool = False
    signals: dict[str, Any] = Field(default_factory=dict)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "agent": "risk-assessment", "version": __version__}


@app.post("/v1/risk/assess", response_model=RiskReport)
async def assess(body: AssessRequest) -> RiskReport:
    score = 18.0 + (body.blocking_findings * 25.0)
    factors = ["context_present"]
    if body.blocking_findings:
        factors.append(f"blocking_findings:{body.blocking_findings}")
    if body.force_high:
        score = max(score, 88.0)
        factors.append("force_high")
    score = min(score, 100.0)
    if score >= 80:
        level = Severity.CRITICAL
    elif score >= 60:
        level = Severity.HIGH
    elif score >= 35:
        level = Severity.MEDIUM
    else:
        level = Severity.LOW

    report = RiskReport(
        score=score,
        level=level,
        factors=factors,
        context_model_id=body.context_model_id,
    )

    llm = _get_llm()
    if llm:
        enhancement = await llm.enhance(
            agent_name="Risk Assessment",
            deterministic_output={
                "score": score,
                "level": level.value,
                "blocking_findings": body.blocking_findings,
                "factors": factors,
                "signals": body.signals,
            },
            context_summary=(
                "Assess AI application risk level. Explain what drives the score, "
                "business impact, and prioritized remediation actions."
            ),
        )
        if enhancement.get("narrative"):
            report = report.model_copy(
                update={
                    "llm_enhancement": {
                        "narrative": enhancement["narrative"],
                        "key_insights": enhancement.get("key_insights", []),
                        "recommendations": enhancement.get("recommendations", []),
                        "model": llm._model_id,
                    }
                }
            )

    return report
