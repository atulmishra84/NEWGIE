from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from gie_observability.logging import configure_logging, get_logger
from gie_observability.tracing import setup_tracing
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
from recommendation_intelligence.adapters.rest.errors import register_exception_handlers
from recommendation_intelligence.adapters.rest.middleware import ObservabilityMiddleware
from recommendation_intelligence.adapters.rest.routes_recommendations import (
    alias,
    router,
)
from recommendation_intelligence.infrastructure.bootstrap import build_container
from recommendation_intelligence.settings import get_settings
from recommendation_intelligence.version import AGENT_NAME, AGENT_VERSION

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
    app.state.container = await build_container(memory=True, settings=settings)
    logger.info("app_started", agent=AGENT_NAME, version=AGENT_VERSION)
    yield
    logger.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GIE Recommendation Intelligence Agent",
        version=AGENT_VERSION,
        description="Prioritized security recommendations (gie.recommendation.v1)",
        lifespan=lifespan,
    )
    app.add_middleware(ObservabilityMiddleware)
    register_exception_handlers(app)
    app.include_router(router)
    app.include_router(alias)

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": AGENT_NAME, "version": AGENT_VERSION}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "agent": AGENT_NAME, "version": AGENT_VERSION}

    @app.get("/ready")
    async def ready():
        return {"ready": True}

    @app.get("/metrics")
    async def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
