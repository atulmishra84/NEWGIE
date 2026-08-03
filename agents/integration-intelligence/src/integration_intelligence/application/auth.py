from __future__ import annotations
from gie_contracts.integration import AuditLogEntry, AuthTokenRequest, AuthTokenResponse
from gie_observability.logging import get_logger
from integration_intelligence.domain.auth_tokens import issue_token
from integration_intelligence.domain.ports import AuditRepository
from integration_intelligence.settings import Settings

logger = get_logger(__name__)

class AuthTokenHandler:
    def __init__(self, *, audits: AuditRepository, settings: Settings):
        self._audits = audits
        self._settings = settings

    async def handle(self, request: AuthTokenRequest, *, actor: str) -> AuthTokenResponse:
        token = issue_token(
            request,
            jwt_secret=self._settings.jwt_secret,
            jwt_algorithm=self._settings.jwt_algorithm,
            mtls_enabled=self._settings.mtls_enabled,
        )
        await self._audits.save(
            AuditLogEntry(
                tenant_id=request.tenant_id,
                actor=actor,
                action="integration.auth.token",
                resource_type="token",
                resource_id=request.subject,
                outcome="success",
                detail={"auth_method": request.auth_method.value, "scopes": request.scopes},
            )
        )
        logger.info("auth_token_issued", method=request.auth_method.value, subject=request.subject)
        return token
