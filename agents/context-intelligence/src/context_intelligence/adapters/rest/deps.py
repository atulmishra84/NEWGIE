"""Authentication and dependency injection for REST API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, AsyncIterator

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from context_intelligence.domain.ports import (
    ContextRepository,
    EventPublisher,
    IdempotencyCache,
    ModelCache,
    OutboxWriter,
    RateLimiter,
)
from context_intelligence.infrastructure.cache.redis_cache import (
    RedisIdempotencyCache,
    RedisModelCache,
    create_redis_client,
)
from context_intelligence.infrastructure.messaging.kafka_publisher import KafkaEventPublisher
from context_intelligence.infrastructure.persistence.database import get_session_factory, session_scope
from context_intelligence.infrastructure.persistence.repositories import (
    SqlAlchemyContextRepository,
    SqlAlchemyOutboxWriter,
)
from context_intelligence.infrastructure.rate_limit import RedisRateLimiter
from context_intelligence.settings import Settings, get_settings
from context_intelligence.version import AGENT_VERSION


@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    subject: str
    roles: frozenset[str]

    def can_read(self) -> bool:
        return "read" in self.roles or "write" in self.roles or "admin" in self.roles

    def can_write(self) -> bool:
        return "write" in self.roles or "admin" in self.roles


def _roles_from_jwt(payload: dict) -> frozenset[str]:
    raw = payload.get("roles") or payload.get("permissions") or ["read"]
    if isinstance(raw, str):
        raw = [raw]
    return frozenset(str(r).lower() for r in raw)


async def get_auth_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AuthContext:
    settings = get_settings()

    if x_api_key:
        async with session_scope() as session:
            repo = SqlAlchemyContextRepository(session)
            record = await repo.validate_api_key(x_api_key)
        if not record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return AuthContext(
            tenant_id=record["tenant_id"],
            subject=record["subject"],
            roles=frozenset(record["roles"]),
        )

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
        tenant_id = payload.get("tenant_id") or payload.get("tid")
        if not tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant_id claim")
        return AuthContext(
            tenant_id=str(tenant_id),
            subject=str(payload.get("sub", "unknown")),
            roles=_roles_from_jwt(payload),
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def require_read(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
    if not auth.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read permission required")
    return auth


def require_write(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
    if not auth.can_write():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Write permission required")
    return auth


async def get_db_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ContextRepository:
    return SqlAlchemyContextRepository(session)


def get_outbox(session: Annotated[AsyncSession, Depends(get_db_session)]) -> OutboxWriter:
    return SqlAlchemyOutboxWriter(session)


_publisher: KafkaEventPublisher | None = None
_redis = None
_idempotency: RedisIdempotencyCache | None = None
_model_cache: RedisModelCache | None = None
_rate_limiter: RedisRateLimiter | None = None


def get_event_publisher() -> EventPublisher:
    global _publisher
    if _publisher is None:
        _publisher = KafkaEventPublisher(get_settings())
    return _publisher


def get_idempotency_cache(settings: Settings = Depends(get_settings)) -> IdempotencyCache:
    global _redis, _idempotency
    if _idempotency is None:
        _redis = create_redis_client(settings)
        _idempotency = RedisIdempotencyCache(_redis, settings.idempotency_ttl_seconds)
    return _idempotency


def get_model_cache(settings: Settings = Depends(get_settings)) -> ModelCache:
    global _redis, _model_cache
    if _model_cache is None:
        if _redis is None:
            _redis = create_redis_client(settings)
        _model_cache = RedisModelCache(_redis, settings.model_cache_ttl_seconds)
    return _model_cache


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    global _redis, _rate_limiter
    if _rate_limiter is None:
        if _redis is None:
            _redis = create_redis_client(settings)
        _rate_limiter = RedisRateLimiter(_redis)
    return _rate_limiter


def get_agent_version() -> str:
    return AGENT_VERSION
