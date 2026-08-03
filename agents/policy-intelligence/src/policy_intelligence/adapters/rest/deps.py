from __future__ import annotations
from fastapi import Depends, Header, HTTPException, Request, status
from gie_security.auth import AuthError, AuthPrincipal, JwtAuthenticator
from policy_intelligence.application.di import Container, get_container
from policy_intelligence.domain.rbac import PolicyPermission, require_policy_permission
from policy_intelligence.settings import get_settings

async def get_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthPrincipal:
    settings = get_settings()
    if not settings.require_auth or settings.gie_env in {"local", "test"}:
        if not authorization and not x_api_key:
            return AuthPrincipal(
                subject_id="local-dev",
                tenant_id=request.headers.get("x-tenant-id", "default"),
                roles=frozenset({"admin"}),
                auth_method="api_key",
            )
    try:
        if authorization:
            return JwtAuthenticator(settings.jwt_secret, algorithm=settings.jwt_algorithm).authenticate_header(authorization)
        if x_api_key and x_api_key.startswith("gie_dev_"):
            return AuthPrincipal(
                subject_id="api-key-user",
                tenant_id=request.headers.get("x-tenant-id", "default"),
                roles=frozenset({"operator"}),
                auth_method="api_key",
            )
        raise AuthError("Missing credentials")
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

def require_perm(permission: PolicyPermission):
    async def _inner(principal: AuthPrincipal = Depends(get_principal)) -> AuthPrincipal:
        require_policy_permission(principal.roles, permission)
        return principal
    return _inner

def container_dep() -> Container:
    return get_container()
