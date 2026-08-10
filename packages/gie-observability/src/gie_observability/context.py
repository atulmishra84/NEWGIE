"""Request-scoped observability context."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import uuid4

from opentelemetry import trace


@dataclass
class ObservabilityContext:
    trace_id: str
    request_id: str
    correlation_id: str
    agent_version: str
    agent_name: str = "context-intelligence"
    tenant_id: str | None = None
    reasoning_path: list[dict] = field(default_factory=list)

    def add_reasoning(
        self, detector_id: str, action: str, detail: str, confidence: float = 0.0
    ) -> None:
        self.reasoning_path.append(
            {
                "step": len(self.reasoning_path) + 1,
                "detector_id": detector_id,
                "action": action,
                "detail": detail,
                "confidence": {"score": confidence},
            }
        )


_CTX: ContextVar[ObservabilityContext | None] = ContextVar("gie_obs_ctx", default=None)


def new_request_context(
    *,
    agent_version: str,
    correlation_id: str | None = None,
    request_id: str | None = None,
    tenant_id: str | None = None,
    agent_name: str = "context-intelligence",
) -> ObservabilityContext:
    span = trace.get_current_span()
    span_ctx = span.get_span_context()
    trace_id = format(span_ctx.trace_id, "032x") if span_ctx.is_valid else uuid4().hex
    ctx = ObservabilityContext(
        trace_id=trace_id,
        request_id=request_id or uuid4().hex,
        correlation_id=correlation_id or uuid4().hex,
        agent_version=agent_version,
        agent_name=agent_name,
        tenant_id=tenant_id,
    )
    _CTX.set(ctx)
    return ctx


def get_context() -> ObservabilityContext | None:
    return _CTX.get()


def bind_context(ctx: ObservabilityContext) -> None:
    _CTX.set(ctx)


def clear_context() -> None:
    _CTX.set(None)
