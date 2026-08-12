"""OAuth / API key / JWT / mTLS token issuance helpers."""

from __future__ import annotations
import hashlib
import hmac
import secrets
import time
from typing import Any
import jwt
from gie_contracts.integration import AuthMethod, AuthTokenRequest, AuthTokenResponse


def issue_token(
    request: AuthTokenRequest,
    *,
    jwt_secret: str,
    jwt_algorithm: str,
    mtls_enabled: bool,
) -> AuthTokenResponse:
    if request.auth_method == AuthMethod.JWT:
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": request.subject,
            "tenant_id": request.tenant_id,
            "scopes": request.scopes,
            "iat": now,
            "exp": now + request.ttl_seconds,
            **request.claims,
        }
        token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
        return AuthTokenResponse(
            token_type="Bearer",
            access_token=token,
            expires_in=request.ttl_seconds,
            scopes=request.scopes,
            auth_method=AuthMethod.JWT,
            mtls_required=mtls_enabled,
        )
    if request.auth_method == AuthMethod.API_KEY:
        raw = f"gie_{secrets.token_urlsafe(24)}"
        return AuthTokenResponse(
            token_type="ApiKey",
            access_token=raw,
            expires_in=request.ttl_seconds,
            scopes=request.scopes,
            auth_method=AuthMethod.API_KEY,
            mtls_required=False,
        )
    if request.auth_method == AuthMethod.OAUTH:
        # Simulated OAuth access token for connector bootstrap
        raw = f"oauth_{secrets.token_urlsafe(32)}"
        return AuthTokenResponse(
            token_type="Bearer",
            access_token=raw,
            expires_in=request.ttl_seconds,
            scopes=request.scopes or ["gie.read", "gie.write"],
            auth_method=AuthMethod.OAUTH,
            mtls_required=False,
        )
    if request.auth_method == AuthMethod.MTLS:
        # Client cert fingerprint placeholder — real mTLS terminates at ingress
        fp = hashlib.sha256(
            f"{request.tenant_id}:{request.subject}".encode()
        ).hexdigest()[:32]
        return AuthTokenResponse(
            token_type="mTLS",
            access_token=f"mtls:{fp}",
            expires_in=request.ttl_seconds,
            scopes=request.scopes,
            auth_method=AuthMethod.MTLS,
            mtls_required=True,
        )
    raise ValueError(f"Unsupported auth method {request.auth_method}")


def verify_webhook_signature(
    payload: bytes, signature: str | None, secret: str
) -> bool:
    if not signature:
        return False
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    expected = signature.removeprefix("sha256=")
    return hmac.compare_digest(digest, expected)
