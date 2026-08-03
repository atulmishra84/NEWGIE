import pytest
from httpx import ASGITransport, AsyncClient
from recommendation_intelligence.adapters.rest.app import create_app
from recommendation_intelligence.infrastructure.bootstrap import build_container
from recommendation_intelligence.settings import Settings

@pytest.mark.asyncio
async def test_generate_get_history_approve(sample_bundle):
    settings = Settings(gie_env="test", require_auth=False)
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/recommendations",
            json={"bundle": sample_bundle.model_dump(mode="json"), "persist": True},
            headers={"x-tenant-id": "acme"},
        )
        assert r.status_code == 200, r.text
        body = r.json()["data"]
        assert body["recommendations"]
        agent_id = body["agent_id"]
        rid = body["recommendations"][0]["recommendation_id"]

        got = await client.get(f"/recommendations/{agent_id}", headers={"x-tenant-id": "acme"})
        assert got.status_code == 200

        hist = await client.get("/recommendations/history", params={"agent_id": agent_id}, headers={"x-tenant-id": "acme"})
        assert hist.status_code == 200
        assert hist.json()["data"]["count"] >= 1

        appr = await client.post(
            "/v1/recommendations/approve",
            json={"tenant_id": "acme", "agent_id": agent_id, "recommendation_ids": [rid]},
            headers={"x-tenant-id": "acme"},
        )
        assert appr.status_code == 200
        approved = [i for i in appr.json()["data"]["recommendations"] if i["recommendation_id"] == rid]
        assert approved[0]["status"] == "approved"
