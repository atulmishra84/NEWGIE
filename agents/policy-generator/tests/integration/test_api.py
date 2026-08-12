import pytest
from httpx import ASGITransport, AsyncClient
from policy_generator.adapters.rest.app import create_app
from policy_generator.infrastructure.bootstrap import build_container
from policy_generator.settings import Settings


@pytest.mark.asyncio
async def test_generate_validate_templates_get(sample_bundle):
    settings = Settings(gie_env="test", require_auth=False)
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/policy/generate",
            json={"bundle": sample_bundle.model_dump(mode="json"), "persist": True},
            headers={"x-tenant-id": "acme"},
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "guardrails.yaml" in data["named_artifacts"]
        assert "openai-policy.json" in data["named_artifacts"]
        package_id = data["package_id"]

        tpl = await client.get("/policy/templates", headers={"x-tenant-id": "acme"})
        assert tpl.status_code == 200
        assert tpl.json()["data"]["count"] >= 18

        got = await client.get(f"/policy/{package_id}", headers={"x-tenant-id": "acme"})
        assert got.status_code == 200

        val = await client.post(
            "/v1/policy/validate",
            json={"package_id": package_id},
            headers={"x-tenant-id": "acme"},
        )
        assert val.status_code == 200
        assert val.json()["data"]["validation"]["status"] in {"valid", "warning"}
