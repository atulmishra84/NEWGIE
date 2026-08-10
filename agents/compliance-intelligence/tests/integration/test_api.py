import pytest
from httpx import ASGITransport, AsyncClient
from compliance_intelligence.adapters.rest.app import create_app
from compliance_intelligence.infrastructure.bootstrap import build_container
from compliance_intelligence.settings import Settings


@pytest.mark.asyncio
async def test_analyze_report_evidence_frameworks(sample_bundle):
    settings = Settings(gie_env="test", require_auth=False)
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/compliance/analyze",
            json={"bundle": sample_bundle.model_dump(mode="json"), "persist": True},
            headers={"x-tenant-id": "acme"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["data"]["compliance_score"] is not None
        assert body["data"]["matrix"]
        app_id = body["data"]["application_id"]

        report = await client.get(
            "/compliance/report",
            params={"application_id": app_id},
            headers={"x-tenant-id": "acme"},
        )
        assert report.status_code == 200
        dash = report.json()["data"]
        assert "compliance_matrix" in dash
        assert "gap_analysis" in dash
        assert "audit_package" in dash

        evid = await client.get(
            "/compliance/evidence",
            params={"application_id": app_id},
            headers={"x-tenant-id": "acme"},
        )
        assert evid.status_code == 200

        fws = await client.get("/frameworks", headers={"x-tenant-id": "acme"})
        assert fws.status_code == 200
        assert fws.json()["data"]["count"] == 14

        v1 = await client.post(
            "/v1/compliance/validate",
            json={
                "tenant_id": "acme",
                "application_id": app_id,
                "implemented_controls": ["soc2-cc6"],
                "evidence": [],
            },
            headers={"x-tenant-id": "acme"},
        )
        assert v1.status_code == 200
