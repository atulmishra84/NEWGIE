"""Command console static serving + JARVIS bridge tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from chief_orchestrator.app import app
from chief_orchestrator import jarvis as jarvis_bridge


@pytest.fixture(autouse=True)
def _reset_jarvis(tmp_path, monkeypatch):
    monkeypatch.setattr(jarvis_bridge.settings, "artifact_dir", str(tmp_path))
    monkeypatch.setattr(jarvis_bridge.settings, "jarvis_enabled", False)
    monkeypatch.setattr(jarvis_bridge.settings, "jarvis_webhook_url", "")
    monkeypatch.setattr(jarvis_bridge.settings, "jarvis_token", "")
    yield


@pytest.mark.asyncio
async def test_health_and_console_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/healthz")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert "console" in body

        root = await client.get("/")
        assert root.status_code == 200
        # Either HTML console or JSON fallback
        ctype = root.headers.get("content-type", "")
        assert "html" in ctype or root.json().get("service") == "gie-chief-orchestrator"


@pytest.mark.asyncio
async def test_jarvis_config_and_forward_disabled():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        got = await client.get("/v1/integrations/jarvis")
        assert got.status_code == 200
        assert got.json()["enabled"] is False

        saved = await client.put(
            "/v1/integrations/jarvis",
            json={
                "enabled": True,
                "webhook_url": "http://127.0.0.1:39999/v1/gie/events",
                "token": "secret",
            },
        )
        assert saved.status_code == 200
        assert saved.json()["enabled"] is True
        assert saved.json()["token_set"] is True

        # No listener — forward reports webhook_error (or rare success if something listens)
        forwarded = await client.post(
            "/v1/integrations/jarvis/forward",
            json={"event": {"type": "ping", "message": "hi"}},
        )
        assert forwarded.status_code == 200
        payload = forwarded.json()
        assert payload.get("forwarded") is True or payload.get("reason") in {
            "jarvis_disabled",
            "missing_webhook_url",
            "webhook_error",
        }
