"""Kafka consumer for context.scan.requested events."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Awaitable
from uuid import UUID

from gie_contracts.events import ContextScanRequested
from gie_observability.logging import get_logger

from context_intelligence.infrastructure.celery_app import execute_scan_task
from context_intelligence.settings import Settings, get_settings

logger = get_logger(__name__)

Handler = Callable[[ContextScanRequested], Awaitable[None]]


async def _default_handler(event: ContextScanRequested) -> None:
    execute_scan_task.delay(
        str(event.scan_id),
        event.tenant_id,
        event.correlation_id,
    )


async def consume_scan_requested(
    handler: Handler | None = None,
    settings: Settings | None = None,
) -> None:
    cfg = settings or get_settings()
    dispatch = handler or _default_handler
    topic = cfg.kafka_topic_scan_requested

    try:
        from aiokafka import AIOKafkaConsumer
    except ImportError:
        logger.error("aiokafka_not_installed")
        raise

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=cfg.kafka_bootstrap_servers,
        group_id=cfg.kafka_consumer_group,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    logger.info("kafka_consumer_started", topic=topic, group=cfg.kafka_consumer_group)
    try:
        async for msg in consumer:
            try:
                event = ContextScanRequested.model_validate(msg.value)
                if event.event_type != "context.scan.requested":
                    continue
                await dispatch(event)
            except Exception:
                logger.exception("kafka_message_handler_failed", offset=msg.offset)
    finally:
        await consumer.stop()


def run_consumer() -> None:
    asyncio.run(consume_scan_requested())
