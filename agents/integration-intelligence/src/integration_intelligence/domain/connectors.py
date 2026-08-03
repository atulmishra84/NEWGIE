"""Connector validation + sync simulation per platform family."""

from __future__ import annotations
from typing import Any
from gie_contracts.integration import AuthMethod, PlatformId, ConnectRequest
from integration_intelligence.domain.catalog import get_platform

class ConnectorError(ValueError):
    pass

def validate_connect(request: ConnectRequest) -> list[str]:
    platform = get_platform(request.platform_id)
    if not platform:
        raise ConnectorError(f"Unknown platform {request.platform_id}")
    reasons: list[str] = []
    if request.auth_method not in platform.auth_methods:
        raise ConnectorError(
            f"Auth method {request.auth_method} not supported for {platform.name}; "
            f"allowed: {[a.value for a in platform.auth_methods]}"
        )
    creds = request.credentials or {}
    if request.auth_method == AuthMethod.API_KEY and not (creds.get("api_key") or creds.get("token")):
        reasons.append("Missing api_key/token credential")
    if request.auth_method == AuthMethod.OAUTH and not (creds.get("client_id") and creds.get("client_secret") or creds.get("access_token")):
        reasons.append("Missing OAuth client_id/client_secret or access_token")
    if request.auth_method == AuthMethod.JWT and not (creds.get("jwt") or creds.get("private_key")):
        reasons.append("Missing jwt or private_key")
    if request.auth_method == AuthMethod.MTLS and not (creds.get("client_cert") or creds.get("cert_fingerprint")):
        reasons.append("Missing client_cert or cert_fingerprint for mTLS")
    # platform-specific hints
    if request.platform_id in {PlatformId.GITHUB, PlatformId.GITHUB_ACTIONS} and not request.config.get("owner"):
        reasons.append("Recommended: set config.owner (org/user)")
    if request.platform_id == PlatformId.AZURE_KEY_VAULT and not request.config.get("vault_uri"):
        reasons.append("Recommended: set config.vault_uri")
    if request.platform_id == PlatformId.HASHICORP_VAULT and not (request.endpoint_url or request.config.get("address")):
        reasons.append("Recommended: set endpoint_url or config.address")
    return reasons

async def simulate_outbound_sync(platform_id: PlatformId, payload: dict[str, Any]) -> tuple[int, int, str]:
    """Simulate push to external platform (no network in unit/local mode)."""
    kind = payload.get("kind") or "policy_bundle"
    count = int(payload.get("count") or len(payload.get("items") or [1]))
    msg = f"Synced {count} {kind} record(s) to {platform_id.value}"
    return count, 0, msg

async def simulate_inbound_sync(platform_id: PlatformId, payload: dict[str, Any]) -> tuple[int, int, str]:
    count = int(payload.get("count") or 1)
    msg = f"Pulled {count} event(s) from {platform_id.value}"
    return 0, count, msg
