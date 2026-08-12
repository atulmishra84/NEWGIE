import pytest
from httpx import ASGITransport, AsyncClient
from learning_intelligence.adapters.rest.app import create_app
from learning_intelligence.infrastructure.bootstrap import build_container
from learning_intelligence.settings import Settings


@pytest.mark.asyncio
async def test_feedback_learn_history_knowledge(sample_bundle):
    settings = Settings(gie_env="test", require_auth=False, allow_auto_publish=False)
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fb = await client.post(
            "/feedback",
            json={
                "event": {
                    "tenant_id": "acme",
                    "agent_id": "agent-checkout-bot",
                    "feedback_type": "user_feedback",
                    "title": "Looks good after tuning",
                    "signals": {"sentiment": "positive"},
                }
            },
            headers={"x-tenant-id": "acme"},
        )
        assert fb.status_code == 200, fb.text

        learned = await client.post(
            "/learn",
            json={"bundle": sample_bundle.model_dump(mode="json"), "persist": True},
            headers={"x-tenant-id": "acme"},
        )
        assert learned.status_code == 200, learned.text
        data = learned.json()["data"]
        assert data["knowledge_changes"]
        assert data["improved_recommendations"]

        hist = await client.get(
            "/learning/history",
            params={"agent_id": "agent-checkout-bot"},
            headers={"x-tenant-id": "acme"},
        )
        assert hist.status_code == 200
        assert hist.json()["data"]["count"] >= 1

        changes = await client.get(
            "/knowledge/changes", headers={"x-tenant-id": "acme"}
        )
        assert changes.status_code == 200
        body = changes.json()["data"]
        assert body["count"] >= 1
        assert body["requires_human_approval_count"] >= 1

        # approve one
        cid = body["items"][0]["change_id"]
        appr = await client.post(
            "/v1/knowledge/approve",
            json={"tenant_id": "acme", "change_ids": [cid]},
            headers={"x-tenant-id": "acme"},
        )
        assert appr.status_code == 200
        assert appr.json()["data"]["count"] == 1
