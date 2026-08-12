"""Exception handlers returning observability envelopes."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from gie_contracts.envelope import ErrorBody, ObservabilityEnvelope, ResponseMeta
from gie_observability.context import get_context
from starlette.exceptions import HTTPException as StarletteHTTPException

from context_intelligence.version import AGENT_NAME, AGENT_VERSION


def _meta(request: Request, *, confidence: float | None = None) -> ResponseMeta:
    ctx = get_context()
    execution_ms = getattr(request.state, "execution_ms", 0.0)
    return ResponseMeta(
        trace_id=ctx.trace_id if ctx else uuid4().hex,
        request_id=ctx.request_id if ctx else uuid4().hex,
        correlation_id=ctx.correlation_id if ctx else uuid4().hex,
        execution_ms=execution_ms,
        confidence=confidence,
        reasoning_path=ctx.reasoning_path if ctx else [],
        agent_version=AGENT_VERSION,
        agent_name=AGENT_NAME,
    )


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> JSONResponse:
    body = ObservabilityEnvelope(
        data=ErrorBody(
            code=code,
            message=message,
            details=details or {},
            retryable=retryable,
            meta=_meta(request),
        ),
        meta=_meta(request),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _error_response(
            request,
            status_code=exc.status_code,
            code="HTTP_ERROR",
            message=detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details={"type": type(exc).__name__},
            retryable=True,
        )
