"""OpenTelemetry tracing setup."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

F = TypeVar("F", bound=Callable[..., Any])


def setup_tracing(
    service_name: str = "context-intelligence",
    service_version: str = "1.0.0",
    otlp_endpoint: str | None = None,
) -> TracerProvider:
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "gie.agent": service_name,
        }
    )
    provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


def traced(name: str | None = None, tracer_name: str = "gie") -> Callable[[F], F]:
    """Wrap sync or async callables in an OpenTelemetry span."""

    def decorator(fn: F) -> F:
        span_name = name or fn.__qualname__
        tracer = trace.get_tracer(tracer_name)

        if asyncio.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(span_name):
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name):
                return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator
