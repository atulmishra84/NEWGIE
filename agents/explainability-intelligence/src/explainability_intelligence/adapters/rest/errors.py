from __future__ import annotations
import time
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gie_security.rbac import PermissionDeniedError
from explainability_intelligence.application.errors import ExplainError, NotFoundError
from explainability_intelligence.version import AGENT_VERSION


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def nf(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404, content=_err(request, exc.code, exc.message)
        )

    @app.exception_handler(ExplainError)
    async def ee(request: Request, exc: ExplainError):
        return JSONResponse(
            status_code=400, content=_err(request, exc.code, exc.message, exc.retryable)
        )

    @app.exception_handler(PermissionDeniedError)
    async def denied(request: Request, exc: PermissionDeniedError):
        return JSONResponse(
            status_code=403, content=_err(request, "forbidden", str(exc))
        )


def _err(request, code, message, retryable=False):
    obs = getattr(request.state, "obs", None)
    started = getattr(request.state, "started", time.perf_counter())
    return {
        "code": code,
        "message": message,
        "retryable": retryable,
        "meta": {
            "trace_id": getattr(obs, "trace_id", uuid4().hex),
            "request_id": getattr(obs, "request_id", uuid4().hex),
            "correlation_id": getattr(obs, "correlation_id", uuid4().hex),
            "execution_ms": (time.perf_counter() - started) * 1000,
            "agent_version": AGENT_VERSION,
            "agent_name": "explainability-intelligence",
        },
    }
