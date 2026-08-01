"""Tests for expanded scope: topology, unsupervised prod flags, CVE wiring."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from chief_orchestrator.app import app
from chief_orchestrator.config import settings
from chief_orchestrator.pipeline import store
from chief_orchestrator.topology import load_topology, production_targets


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    store.runs.clear()
    store.traces.clear()
    store.latest_golden_run_id = None
    monkeypatch.setattr(settings, "allow_customer_prod", False)
    monkeypatch.setattr(settings, "unsupervised_prod", False)
    monkeypatch.setattr(settings, "cve_providers", "osv")
    yield


def test_multi_region_topology_loads():
    topo = load_topology()
    assert len(topo.get("regions", [])) >= 2
    targets = production_targets(topo)
    assert any(t["region"] == "us-east-1" for t in targets)
    assert any(t["region"] == "eu-west-1" for t in targets)


@pytest.mark.asyncio
async def test_status_exposes_expanded_capabilities():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        status = await client.post("/v1/command", json={"text": "status", "channel": "text"})
        body = status.json()["result"]
        assert "regions" in body
        assert body["voice"]["stt_provider"]
        assert "osv" in body["cve_providers"]


@pytest.mark.asyncio
async def test_unsupervised_prod_promote(monkeypatch):
    monkeypatch.setattr(settings, "allow_customer_prod", True)
    monkeypatch.setattr(settings, "unsupervised_prod", True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        golden = await client.post(
            "/v1/command",
            json={
                "text": (
                    "Build the golden demo app, run full security and QA, "
                    "scan with GIE, deploy to staging, and show me the result."
                ),
                "channel": "text",
            },
        )
        body = golden.json()
        assert body["status"] == "succeeded"
        steps = {s["agent_id"] for s in body["run"]["steps"]}
        assert "devops" in steps
        assert body["run"]["human_approved"] is True
        assert "prod_promote" in (body["run"]["evidence"]["reports"] or {})

        prod = await client.get("/demo/prod/us-east-1")
        assert prod.json()["env"] == "production"
