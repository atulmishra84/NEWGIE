import hashlib
import hmac
import json
import pytest
from httpx import ASGITransport, AsyncClient
from integration_intelligence.adapters.rest.app import create_app
from integration_intelligence.infrastructure.bootstrap import build_container
from integration_intelligence.settings import Settings


@pytest.mark.asyncio
async def test_catalog_connect_sync_webhook_auth_audit(sample_connect):
    settings = Settings(
        gie_env="test",
        require_auth=False,
        webhook_hmac_secret="whsec",
        retry_max_attempts=2,
        retry_base_delay_ms=1,
    )
    await build_container(memory=True, settings=settings)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cat = await client.get("/integrations", headers={"x-tenant-id": "acme"})
        assert cat.status_code == 200
        assert cat.json()["data"]["count"] >= 28

        conn_r = await client.post(
            "/integrations/connect",
            json=sample_connect.model_dump(mode="json"),
            headers={"x-tenant-id": "acme"},
        )
        assert conn_r.status_code == 200, conn_r.text
        cid = conn_r.json()["data"]["connection_id"]

        sync = await client.post(
            f"/integrations/{cid}/sync",
            json={
                "tenant_id": "acme",
                "payload": {"kind": "policy_bundle", "count": 2},
            },
            headers={"x-tenant-id": "acme"},
        )
        assert sync.status_code == 200
        assert sync.json()["data"]["status"] == "success"

        payload = {
            "tenant_id": "acme",
            "event_type": "push",
            "payload": {"ref": "main"},
        }
        raw = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(b"whsec", raw, hashlib.sha256).hexdigest()
        wh = await client.post(
            "/webhooks/github",
            content=raw,
            headers={
                "x-tenant-id": "acme",
                "content-type": "application/json",
                "x-gie-signature": sig,
            },
        )
        assert wh.status_code == 200
        assert wh.json()["data"]["signature_valid"] is True

        tok = await client.post(
            "/auth/token",
            json={
                "tenant_id": "acme",
                "auth_method": "jwt",
                "subject": "svc",
                "scopes": ["gie.read"],
            },
            headers={"x-tenant-id": "acme"},
        )
        assert tok.status_code == 200
        assert tok.json()["data"]["access_token"]

        audit = await client.get("/audit", headers={"x-tenant-id": "acme"})
        assert audit.status_code == 200
        assert audit.json()["data"]["count"] >= 3

        health = await client.get(
            "/integrations/health/report", headers={"x-tenant-id": "acme"}
        )
        assert health.status_code == 200
        assert "connected" in health.json()["data"]
