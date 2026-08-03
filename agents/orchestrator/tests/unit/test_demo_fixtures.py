from orchestrator.domain.demo_fixtures import demo_payload, is_demo_request


def test_is_demo_request_by_tenant_and_path():
    assert is_demo_request({"tenant_id": "acme", "source": {"path": "/x"}})
    assert is_demo_request({"tenant_id": "other", "source": {"path": "/demo/acme-ai-assistant"}})
    assert is_demo_request({"tenant_id": "other", "options": {"demo": True}})
    assert not is_demo_request({"tenant_id": "prod", "source": {"path": "/srv/app"}})


def test_demo_payload_has_summary_and_confidence():
    out = demo_payload("risk", "1.0.0", {"tenant_id": "acme", "source": {"path": "/demo/acme-ai-assistant"}})
    assert out["agent_id"] == "risk"
    assert out["demo"] is True
    assert out["score"] == 72
    assert out["confidence"] >= 0.8
    assert "findings" in out
