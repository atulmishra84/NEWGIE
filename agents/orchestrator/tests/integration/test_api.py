import pytest
from httpx import ASGITransport, AsyncClient
from orchestrator.adapters.rest.app import create_app
from orchestrator.infrastructure.bootstrap import build_container
from orchestrator.settings import Settings


@pytest.mark.asyncio
async def test_analyze_status_execution_trace(sample_analyze):
    settings = Settings(
        gie_env="test", require_auth=False, simulate_agents=True, retry_base_delay_ms=1
    )
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/analyze",
            json=sample_analyze.model_dump(mode="json"),
            headers={"x-tenant-id": "acme"},
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["status"] == "completed"
        eid = data["execution_id"]
        tid = data["trace_id"]

        st = await client.get("/status", headers={"x-tenant-id": "acme"})
        assert st.status_code == 200
        assert st.json()["data"]["healthy"] is True
        assert len(st.json()["data"]["agents"]) >= 9

        ex = await client.get(f"/execution/{eid}", headers={"x-tenant-id": "acme"})
        assert ex.status_code == 200
        assert ex.json()["data"]["execution_id"] == eid

        tr = await client.get(f"/trace/{tid}", headers={"x-tenant-id": "acme"})
        assert tr.status_code == 200
        assert tr.json()["data"]["spans"]

        g = await client.get("/graph", headers={"x-tenant-id": "acme"})
        assert g.status_code == 200
        assert "mermaid" in g.json()["data"]
        waves = g.json()["data"]["waves"]
        assert any(set(w) == {"risk", "compliance"} for w in waves)

        wf = await client.post(
            "/workflow",
            json={
                "tenant_id": "acme",
                "mode": "sync",
                "workflow": {
                    "workflow_id": "custom",
                    "name": "tiny",
                    "parallel_enabled": False,
                    "steps": [
                        {"step_id": "context", "agent_id": "context", "depends_on": []},
                        {
                            "step_id": "knowledge",
                            "agent_id": "knowledge",
                            "depends_on": ["context"],
                        },
                    ],
                },
                "input": {"source": {"path": "/y"}},
            },
            headers={"x-tenant-id": "acme"},
        )
        assert wf.status_code == 200
        assert wf.json()["data"]["status"] == "completed"
