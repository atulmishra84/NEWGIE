"""Unit tests for orchestrator voice ingress and pipeline gates."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from chief_orchestrator.app import app
from chief_orchestrator.pipeline import store
from chief_orchestrator.voice import normalize_intent, synthesize_tts_sync_stub
from gie_contracts import Channel, IntentType


@pytest.fixture(autouse=True)
def _reset_store():
    store.runs.clear()
    store.traces.clear()
    store.latest_golden_run_id = None
    store.live_checks.clear()
    yield


def test_tts_wav_header():
    audio = synthesize_tts_sync_stub("hello fleet")
    assert audio[:4] == b"RIFF"
    assert b"WAVE" in audio[:12]


def test_ambiguous_intent():
    intent = normalize_intent(text="ummm", channel=Channel.VOICE)
    assert intent.needs_clarification
    assert intent.intent == IntentType.CLARIFY


def test_prod_requires_confirm():
    intent = normalize_intent(text="approve production please", channel=Channel.VOICE)
    assert intent.intent == IntentType.PROD_APPROVE
    assert not intent.prod_confirmed


@pytest.mark.asyncio
async def test_status_and_golden_and_gates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/healthz")
        assert health.status_code == 200

        status = await client.post("/v1/command", json={"text": "status", "channel": "text"})
        assert status.status_code == 200
        body = status.json()
        assert body["result"]["fleet_size"] >= 16

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
        g = golden.json()
        assert g["status"] == "succeeded"
        assert g["run"]["evidence"]["staging_url"]

        blocked = await client.post(
            "/v1/command",
            json={
                "text": (
                    "Build the golden demo app, run full security and QA, "
                    "scan with GIE, deploy to staging, and show me the result."
                ),
                "channel": "text",
                "inject_critical_finding": True,
            },
        )
        assert blocked.json()["status"] == "blocked"

        deny = await client.post(
            "/v1/command",
            json={
                "text": (
                    "Build the golden demo app, run full security and QA, "
                    "scan with GIE, deploy to staging, and show me the result."
                ),
                "channel": "text",
                "force_policy_deny": True,
            },
        )
        assert deny.json()["status"] == "blocked"

        dry = await client.post(
            "/v1/command",
            json={
                "text": "approve production deploy",
                "channel": "text",
                "prod_confirm_phrase": "approve production deploy",
            },
        )
        assert dry.json()["result"]["customer_prod_touched"] is False
