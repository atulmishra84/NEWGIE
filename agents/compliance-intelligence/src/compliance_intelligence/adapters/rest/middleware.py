from __future__ import annotations
import time
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from gie_observability.context import clear_context, new_request_context
from compliance_intelligence.version import AGENT_NAME, AGENT_VERSION

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        ctx = new_request_context(agent_version=AGENT_VERSION, correlation_id=request.headers.get("x-correlation-id") or uuid4().hex, request_id=request.headers.get("x-request-id") or uuid4().hex, agent_name=AGENT_NAME)
        request.state.obs = ctx
        request.state.started = started
        try:
            response = await call_next(request)
        finally:
            clear_context()
        response.headers["x-trace-id"] = ctx.trace_id
        response.headers["x-request-id"] = ctx.request_id
        response.headers["x-correlation-id"] = ctx.correlation_id
        response.headers["x-agent-version"] = AGENT_VERSION
        response.headers["x-execution-ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
        return response
