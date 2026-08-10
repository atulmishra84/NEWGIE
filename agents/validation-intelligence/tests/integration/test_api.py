import pytest
from httpx import ASGITransport, AsyncClient
from validation_intelligence.adapters.rest.app import create_app
from validation_intelligence.infrastructure.bootstrap import build_container
from validation_intelligence.settings import Settings


@pytest.mark.asyncio
async def test_validate_simulate_get_report(sample_bundle):
    settings = Settings(gie_env="test", require_auth=False)
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/validate",
            json={
                "bundle": sample_bundle.model_dump(mode="json"),
                "persist": True,
                "run_simulation": True,
            },
            headers={"x-tenant-id": "acme"},
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        vid = data["validation_id"]
        assert data["verdict"] in {"pass", "warning", "failed"}
        assert data["approval_status"]

        got = await client.get(f"/validation/{vid}", headers={"x-tenant-id": "acme"})
        assert got.status_code == 200

        report = await client.get(
            "/validation/report",
            params={"agent_id": "agent-checkout-bot"},
            headers={"x-tenant-id": "acme"},
        )
        assert report.status_code == 200
        assert "approval_status" in report.json()["data"]

        sim = await client.post(
            "/v1/simulate",
            json={
                "tenant_id": "acme",
                "agent_id": "agent-checkout-bot",
                "policy_package": sample_bundle.policy_package,
            },
            headers={"x-tenant-id": "acme"},
        )
        assert sim.status_code == 200
        assert sim.json()["data"]["simulations"]
