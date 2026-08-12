from __future__ import annotations

import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gie_security.rbac import PermissionDeniedError

from knowledge_intelligence.application.errors import KnowledgeError, NotFoundError
from knowledge_intelligence.version import AGENT_VERSION


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404, content=_err(request, exc.code, exc.message, False)
        )

    @app.exception_handler(KnowledgeError)
    async def knowledge_err(request: Request, exc: KnowledgeError):
        return JSONResponse(
            status_code=400, content=_err(request, exc.code, exc.message, exc.retryable)
        )

    @app.exception_handler(PermissionDeniedError)
    async def denied(request: Request, exc: PermissionDeniedError):
        return JSONResponse(
            status_code=403, content=_err(request, "forbidden", str(exc), False)
        )


def _err(request: Request, code: str, message: str, retryable: bool) -> dict:
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
            "agent_name": "knowledge-intelligence",
        },
    }
