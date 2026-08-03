import pytest
from gie_contracts.integration import AuthMethod, AuthTokenRequest, ConnectionStatus, IntegrationConnection, PlatformId, SyncRequest
from integration_intelligence.domain.auth_tokens import issue_token, verify_webhook_signature
from integration_intelligence.domain.engine import run_sync
from integration_intelligence.domain.resilience import CircuitOpenError, ensure_circuit_allows

def test_issue_jwt_and_api_key():
    jwt_tok = issue_token(
        AuthTokenRequest(tenant_id="acme", auth_method=AuthMethod.JWT, subject="u1", scopes=["gie.read"]),
        jwt_secret="secret",
        jwt_algorithm="HS256",
        mtls_enabled=False,
    )
    assert jwt_tok.token_type == "Bearer"
    assert jwt_tok.access_token
    key = issue_token(
        AuthTokenRequest(tenant_id="acme", auth_method=AuthMethod.API_KEY, subject="u1"),
        jwt_secret="secret",
        jwt_algorithm="HS256",
        mtls_enabled=False,
    )
    assert key.access_token.startswith("gie_")

def test_webhook_signature():
    ok = verify_webhook_signature(b'{"a":1}', None, "sec")
    assert ok is False

@pytest.mark.asyncio
async def test_circuit_opens_after_failures():
    conn = IntegrationConnection(
        tenant_id="acme",
        platform_id=PlatformId.SPLUNK,
        name="splunk",
        auth_method=AuthMethod.API_KEY,
        status=ConnectionStatus.CONNECTED,
    )
    for _ in range(3):
        result = await run_sync(
            conn,
            SyncRequest(connection_id=conn.connection_id, tenant_id="acme", payload={"_force_fail": True}),
            failure_threshold=3,
            open_seconds=60,
            max_attempts=1,
            base_delay_ms=1,
        )
    assert conn.circuit_breaker_state == "open"
    assert result.status == "circuit_open"
    with pytest.raises(CircuitOpenError):
        ensure_circuit_allows(conn, open_seconds=60)
