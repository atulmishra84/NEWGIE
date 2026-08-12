import pytest
from httpx import ASGITransport, AsyncClient
from explainability_intelligence.adapters.rest.app import create_app
from explainability_intelligence.infrastructure.bootstrap import build_container
from explainability_intelligence.settings import Settings


@pytest.mark.asyncio
async def test_explain_get_reasoning_figma(sample_bundle):
    settings = Settings(gie_env="test", require_auth=False)
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/explain",
            json={"bundle": sample_bundle.model_dump(mode="json"), "persist": True},
            headers={"x-tenant-id": "acme"},
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        eid = data["explanation_id"]
        assert len(data["views"]) == 5
        assert data["artifacts"]

        got = await client.get(f"/explanation/{eid}", headers={"x-tenant-id": "acme"})
        assert got.status_code == 200

        path = await client.post(
            "/reasoning/path",
            json={
                "tenant_id": "acme",
                "decision_id": "rec-prompt-injection-abc",
                "steps": [],
            },
            headers={"x-tenant-id": "acme"},
        )
        assert path.status_code == 200
        assert path.json()["data"]["mermaid_diagram"]

        fig = await client.get(
            "/figma-generate-diagram",
            params={"explanation_id": eid},
            headers={"x-tenant-id": "acme"},
        )
        assert fig.status_code == 200
        assert fig.json()["data"]["tool"] == "generate_diagram"
