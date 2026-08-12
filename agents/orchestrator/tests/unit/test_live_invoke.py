"""Unit tests for live invoke normalizers (no network)."""

from orchestrator.domain.live_invoke import (
    normalize_compliance,
    normalize_generator,
    normalize_recommendation,
    normalize_risk,
    normalize_validation,
)


def test_normalize_risk_scales_score_to_100():
    out = normalize_risk(
        {
            "overall_ai_risk_score": 0.72,
            "severity": "high",
            "confidence": {"score": 0.8},
            "factors": [
                {
                    "factor_id": "rf1",
                    "name": "Prompt injection",
                    "severity": "high",
                    "score": 0.8,
                }
            ],
        }
    )
    assert out["score"] == 72
    assert out["findings"][0]["title"] == "Prompt injection"
    assert out["confidence"] == 0.8


def test_normalize_recommendation_maps_priorities():
    out = normalize_recommendation(
        {
            "recommendations": [
                {
                    "recommendation_id": "r1",
                    "title": "Add firewall",
                    "priority": "critical",
                },
                {
                    "recommendation_id": "r2",
                    "title": "Redact PII",
                    "priority": "medium",
                },
            ],
            "confidence": {"score": 0.9},
        }
    )
    assert out["actions"][0]["priority"] == 1
    assert out["actions"][1]["priority"] == 2
    assert "Add firewall" in out["actions"][0]["title"]


def test_normalize_compliance_and_generator_and_validation():
    c = normalize_compliance(
        {
            "compliance_score": 0.55,
            "gaps": [
                {
                    "control_id": "GOVERN-1.2",
                    "status": "missing",
                    "description": "No owner",
                }
            ],
            "applicable_frameworks": [{"framework": "soc2", "applicable": True}],
            "confidence": 0.7,
        }
    )
    assert c["gaps"][0]["control"] == "GOVERN-1.2"
    assert "soc2" in c["frameworks"]

    g = normalize_generator(
        {
            "package_id": "pkg1",
            "policies": [
                {
                    "metadata": {"name": "prompt-firewall"},
                    "format": "yaml",
                    "content": "x: 1",
                }
            ],
            "confidence": {"score": 0.81},
        }
    )
    assert g["artifacts"]["items"][0]["name"].startswith("prompt-firewall")

    v = normalize_validation(
        {
            "verdict": "pass",
            "approval_status": "approved",
            "checks": [{"category": "syntax", "verdict": "pass", "message": "ok"}],
            "confidence": {"score": 0.77},
        }
    )
    assert v["results"][0]["status"] == "pass"
