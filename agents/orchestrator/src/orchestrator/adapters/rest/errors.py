from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gie_security.rbac import PermissionDeniedError
from orchestrator.application.errors import NotFoundError, OrchestratorError

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(OrchestratorError)
    async def orch_err(_: Request, exc: OrchestratorError):
        return JSONResponse(status_code=400, content={"error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(PermissionDeniedError)
    async def denied(_: Request, exc: PermissionDeniedError):
        return JSONResponse(status_code=403, content={"error": {"code": "forbidden", "message": str(exc)}})
