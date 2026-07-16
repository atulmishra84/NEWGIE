#!/usr/bin/env python3
"""Bootstrap GIE Context Intelligence Agent monorepo files."""
from __future__ import annotations

from pathlib import Path

ROOT = Path("/Users/mac/GIE")


def w(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content[1:] if content.startswith("\n") else content
    path.write_text(text)
    print(f"wrote {rel}")


def main() -> None:
    # Observability logging
    w(
        "packages/gie-observability/src/gie_observability/logging.py",
        r'''
"""Structured JSON logging via structlog."""

from __future__ import annotations

import logging
import sys

import structlog

from gie_observability.context import get_context


def _add_obs_context(logger: logging.Logger, method_name: str, event_dict: dict) -> dict:
    ctx = get_context()
    if ctx:
        event_dict.setdefault("trace_id", ctx.trace_id)
        event_dict.setdefault("request_id", ctx.request_id)
        event_dict.setdefault("correlation_id", ctx.correlation_id)
        event_dict.setdefault("agent_version", ctx.agent_version)
        if ctx.tenant_id:
            event_dict.setdefault("tenant_id", ctx.tenant_id)
    return event_dict


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_obs_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
''',
    )

    w(
        "packages/gie-observability/src/gie_observability/tracing.py",
        r'''
"""OpenTelemetry tracing setup."""

from __future__ import annotations

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
            "gie.agent": "context-intelligence",
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


def traced(name: str | None = None) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        span_name = name or fn.__qualname__
        tracer = trace.get_tracer("gie.context-intelligence")

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
''',
    )

    w(
        "packages/gie-observability/src/gie_observability/metrics.py",
        r'''
"""Prometheus-compatible metrics helpers."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

SCAN_REQUESTS = Counter(
    "gie_context_scan_requests_total",
    "Total scan requests",
    ["tenant_id", "source_type", "status"],
)
SCAN_DURATION = Histogram(
    "gie_context_scan_duration_seconds",
    "Scan duration in seconds",
    ["source_type"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)
MODEL_GETS = Counter(
    "gie_context_model_gets_total",
    "Context model GET requests",
    ["cache_hit"],
)
ACTIVE_SCANS = Gauge(
    "gie_context_active_scans",
    "Currently running scans",
)
''',
    )

    w(
        "packages/gie-observability/pyproject.toml",
        r'''
[project]
name = "gie-observability"
version = "1.0.0"
description = "OpenTelemetry, correlation IDs, structured logging for GIE"
requires-python = ">=3.12"
dependencies = [
  "opentelemetry-api>=1.25",
  "opentelemetry-sdk>=1.25",
  "opentelemetry-exporter-otlp>=1.25",
  "opentelemetry-instrumentation-fastapi>=0.46b0",
  "structlog>=24.1",
  "prometheus-client>=0.20",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gie_observability"]
''',
    )

    print("phase1 complete")


if __name__ == "__main__":
    main()
