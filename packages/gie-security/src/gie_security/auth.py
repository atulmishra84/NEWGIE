"""JWT (HS256) and API key authentication primitives."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from pydantic import BaseModel, Field, field_validator

AuthMethod = Literal["jwt", "api_key"]


class AuthError(Exception):
    """Base authentication error."""


class TokenInvalidError(AuthError):
    """JWT is malformed or signature verification failed."""


class TokenExpiredError(AuthError):
    """JWT has expired."""


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    """Authenticated caller identity bound to a tenant."""

    subject_id: str
    tenant_id: str
    roles: frozenset[str]
    auth_method: AuthMethod
    email: str | None = None
    scopes: frozenset[str] = field(default_factory=frozenset)

    def has_role(self, role: str) -> bool:
        return role in self.roles


class JwtClaims(BaseModel):
    """Validated JWT payload for GIE services."""

    sub: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)
    email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    exp: int | None = None
    iat: int | None = None
    iss: str | None = None
    aud: str | None = None

    @field_validator("roles", mode="before")
    @classmethod
    def _normalize_roles(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    @field_validator("scopes", mode="before")
    @classmethod
    def _normalize_scopes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    def to_principal(self) -> AuthPrincipal:
        return AuthPrincipal(
            subject_id=self.sub,
            tenant_id=self.tenant_id,
            roles=frozenset(self.roles),
            auth_method="jwt",
            email=self.email,
            scopes=frozenset(self.scopes),
        )


class JwtAuthenticator:
    """Create and verify HS256 JWT access tokens."""

    def __init__(
        self,
        secret: str,
        *,
        algorithm: str = "HS256",
        issuer: str | None = "gie",
        audience: str | None = None,
        default_ttl: timedelta = timedelta(hours=1),
    ) -> None:
        if not secret:
            raise ValueError("JWT secret must not be empty")
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._default_ttl = default_ttl

    def issue_token(
        self,
        principal: AuthPrincipal,
        *,
        ttl: timedelta | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        expires = now + (ttl or self._default_ttl)
        payload: dict[str, Any] = {
            "sub": principal.subject_id,
            "tenant_id": principal.tenant_id,
            "roles": sorted(principal.roles),
            "scopes": sorted(principal.scopes),
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        }
        if principal.email:
            payload["email"] = principal.email
        if self._issuer:
            payload["iss"] = self._issuer
        if self._audience:
            payload["aud"] = self._audience
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> AuthPrincipal:
        try:
            options: dict[str, Any] = {"require": ["exp", "sub", "tenant_id"]}
            decode_kwargs: dict[str, Any] = {
                "algorithms": [self._algorithm],
                "options": options,
            }
            if self._issuer:
                decode_kwargs["issuer"] = self._issuer
            if self._audience:
                decode_kwargs["audience"] = self._audience
            raw = jwt.decode(token, self._secret, **decode_kwargs)
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError("JWT has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise TokenInvalidError("JWT is invalid") from exc

        claims = JwtClaims.model_validate(raw)
        return claims.to_principal()

    def authenticate_header(self, authorization: str | None) -> AuthPrincipal:
        if not authorization:
            raise AuthError("Missing Authorization header")
        scheme, _, credential = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            raise AuthError("Authorization header must be Bearer <token>")
        return self.verify_token(credential.strip())


class ApiKeyHasher:
    """Hash and verify API keys with a server-side pepper."""

    def __init__(self, pepper: str, *, iterations: int = 100_000) -> None:
        if not pepper:
            raise ValueError("API key pepper must not be empty")
        self._pepper = pepper.encode("utf-8")
        self._iterations = iterations

    def hash_key(self, raw_key: str) -> str:
        if not raw_key:
            raise ValueError("API key must not be empty")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            raw_key.encode("utf-8"),
            self._pepper,
            self._iterations,
        )
        return digest.hex()

    def verify_key(self, raw_key: str, stored_hash: str) -> bool:
        if not raw_key or not stored_hash:
            return False
        computed = self.hash_key(raw_key)
        return hmac.compare_digest(computed, stored_hash)

    def principal_from_record(
        self,
        *,
        subject_id: str,
        tenant_id: str,
        roles: list[str] | frozenset[str],
        email: str | None = None,
        scopes: list[str] | frozenset[str] | None = None,
    ) -> AuthPrincipal:
        return AuthPrincipal(
            subject_id=subject_id,
            tenant_id=tenant_id,
            roles=frozenset(roles),
            auth_method="api_key",
            email=email,
            scopes=frozenset(scopes or []),
        )

    def authenticate(
        self,
        raw_key: str,
        stored_hash: str,
        *,
        subject_id: str,
        tenant_id: str,
        roles: list[str] | frozenset[str],
        email: str | None = None,
        scopes: list[str] | frozenset[str] | None = None,
    ) -> AuthPrincipal:
        if not self.verify_key(raw_key, stored_hash):
            raise AuthError("Invalid API key")
        return self.principal_from_record(
            subject_id=subject_id,
            tenant_id=tenant_id,
            roles=roles,
            email=email,
            scopes=scopes,
        )

    @staticmethod
    def generate_key(prefix: str = "gie", nbytes: int = 32) -> str:
        token = secrets.token_urlsafe(nbytes)
        return f"{prefix}_{token}"
