from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gie_observability.logging import configure_logging, get_logger
from gie_observability.tracing import setup_tracing
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
from orchestrator.adapters.rest.errors import register_exception_handlers
from orchestrator.adapters.rest.middleware import ObservabilityMiddleware
from orchestrator.adapters.rest.routes_orchestrator import alias, router
from orchestrator.infrastructure.bootstrap import build_container
from orchestrator.settings import get_settings
from orchestrator.version import AGENT_NAME, AGENT_VERSION

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
    settings = get_settings()
    app = FastAPI(
        title="GIE Orchestrator Agent",
        version=AGENT_VERSION,
        description="Coordinates every agent in Guardrails Intelligence Engine (gie.orchestrator.v1)",
        lifespan=lifespan,
    )
    # Allow static dashboard (web/) and sandbox UIs to call the API from a browser.
    cors_origins = (
        ["*"]
        if (not settings.require_auth)
        or settings.gie_env in {"local", "test", "docker", "dev", "azure"}
        else [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ObservabilityMiddleware)
    register_exception_handlers(app)
    app.include_router(router)
    app.include_router(alias)

    @app.get("/")
    async def root():
        return {
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "schema": "gie.orchestrator.v1",
            "docs": "/docs",
            "health": "/healthz",
            "endpoints": {
                "analyze": "POST /analyze",
                "workflow": "POST /workflow",
                "status": "GET /status",
                "execution": "GET /execution/{id}",
                "trace": "GET /trace/{id}",
                "graph": "GET /graph",
                "approve": "POST /approve",
            },
        }

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
