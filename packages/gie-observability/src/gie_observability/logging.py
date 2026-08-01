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
