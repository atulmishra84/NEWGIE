from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gie_security.rbac import PermissionDeniedError
from integration_intelligence.application.errors import IntegrationError, NotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(IntegrationError)
    async def integration_err(_: Request, exc: IntegrationError):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(PermissionDeniedError)
    async def denied(_: Request, exc: PermissionDeniedError):
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "forbidden", "message": str(exc)}},
        )
