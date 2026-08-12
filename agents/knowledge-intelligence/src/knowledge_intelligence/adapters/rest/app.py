"""FastAPI entrypoint for Knowledge Intelligence Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from gie_observability.logging import configure_logging, get_logger
from gie_observability.tracing import setup_tracing
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from knowledge_intelligence.adapters.rest.errors import register_exception_handlers
from knowledge_intelligence.adapters.rest.middleware import ObservabilityMiddleware
from knowledge_intelligence.adapters.rest.routes_knowledge import (
    router as knowledge_router,
)
from knowledge_intelligence.adapters.webhooks.inbound import router as webhook_router
from knowledge_intelligence.infrastructure.bootstrap import build_container
from knowledge_intelligence.seed.loader import seed_builtin_knowledge
from knowledge_intelligence.settings import get_settings
from knowledge_intelligence.version import AGENT_NAME, AGENT_VERSION

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(level=settings.log_level)
    setup_tracing(
        service_name=AGENT_NAME,
        service_version=AGENT_VERSION,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint or None,
    )
    use_memory = settings.gie_env in {"local", "test"}
    try:
        container = await build_container(memory=use_memory, settings=settings)
    except Exception as exc:
        logger.warning("falling_back_to_memory", error=str(exc))
        container = await build_container(memory=True, settings=settings)
    app.state.container = container
    if settings.flag_enable_reindex_on_start:
        count = await seed_builtin_knowledge(container)
        logger.info("seeded_knowledge", nodes=count)
    logger.info("app_started", agent=AGENT_NAME, version=AGENT_VERSION)
    yield
    await container.graph.close()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GIE Knowledge Intelligence Agent",
        version=AGENT_VERSION,
        description="Versioned knowledge graph brain of Guardrails Intelligence Engine (gie.knowledge.v1)",
        lifespan=lifespan,
    )
    app.add_middleware(ObservabilityMiddleware)
    register_exception_handlers(app)
    app.include_router(knowledge_router)
    app.include_router(webhook_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": AGENT_NAME, "version": AGENT_VERSION}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "agent": AGENT_NAME, "version": AGENT_VERSION}

    @app.get("/ready")
    async def ready():
        c = app.state.container
        return {
            "ready": True,
            "checks": {
                "graph": await c.graph.ping(),
                "vectors": await c.vectors.ping(),
            },
        }

    @app.get("/metrics")
    async def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
