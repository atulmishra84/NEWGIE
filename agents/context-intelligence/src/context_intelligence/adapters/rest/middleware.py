"""HTTP middleware for correlation IDs, timing, and envelope metadata."""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Request, Response
from gie_observability.context import bind_context, clear_context, new_request_context
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from context_intelligence.version import AGENT_NAME, AGENT_VERSION


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or uuid4().hex
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        tenant_id = request.headers.get("X-Tenant-ID")

        ctx = new_request_context(
            agent_version=AGENT_VERSION,
            correlation_id=correlation_id,
            request_id=request_id,
            tenant_id=tenant_id,
            agent_name=AGENT_NAME,
        )
        bind_context(ctx)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Correlation-ID"] = ctx.correlation_id
        response.headers["X-Request-ID"] = ctx.request_id
        response.headers["X-Execution-Ms"] = f"{elapsed_ms:.2f}"
        response.headers["X-Agent-Version"] = AGENT_VERSION
        request.state.execution_ms = elapsed_ms
        request.state.obs_context = ctx

        clear_context()
        return response
