"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from gie_observability.logging import configure_logging, get_logger
from gie_observability.tracing import setup_tracing
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from context_intelligence.adapters.rest.errors import register_exception_handlers
from context_intelligence.adapters.rest.middleware import ObservabilityMiddleware
from context_intelligence.adapters.rest.routes_models import router as models_router
from context_intelligence.adapters.webhooks.github import router as github_router
from context_intelligence.infrastructure.cache.redis_cache import create_redis_client, ping_redis
from context_intelligence.infrastructure.persistence.database import check_db, init_db
from context_intelligence.infrastructure.persistence.neo4j_repo import Neo4jGraphRepository
from context_intelligence.infrastructure.persistence.qdrant_store import QdrantEvidenceVectorStore
from context_intelligence.settings import get_settings
from context_intelligence.version import AGENT_NAME, AGENT_VERSION

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(level=settings.log_level)
    setup_tracing(
        service_name=AGENT_NAME,
        service_version=AGENT_VERSION,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
    await init_db()
    app.state.redis = create_redis_client(settings)
    app.state.neo4j = Neo4jGraphRepository.from_settings(settings)
    app.state.qdrant = QdrantEvidenceVectorStore.from_settings(settings)
    logger.info("app_started", agent=AGENT_NAME, version=AGENT_VERSION)
    yield
    await app.state.neo4j.close()
    await app.state.redis.aclose()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GIE Context Intelligence Agent",
        version=AGENT_VERSION,
        description="Scan AI projects into normalized context models (gie.context.v1)",
        lifespan=lifespan,
    )
    app.add_middleware(ObservabilityMiddleware)
    register_exception_handlers(app)
    app.include_router(scans_router)
    app.include_router(models_router)
    app.include_router(github_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "agent": AGENT_NAME, "version": AGENT_VERSION}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "agent": AGENT_NAME, "version": AGENT_VERSION}

    @app.get("/ready")
    async def ready() -> dict[str, object]:
        db_ok = await check_db()
        redis_ok = await ping_redis(app.state.redis)
        neo4j_ok = await app.state.neo4j.ping()
        qdrant_ok = await app.state.qdrant.ping()
        ready = db_ok and redis_ok
        return {
            "ready": ready,
            "checks": {"database": db_ok, "redis": redis_ok, "neo4j": neo4j_ok, "qdrant": qdrant_ok},
        }

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    FastAPIInstrumentor.instrument_app(app)
    return app


app = create_app()
