"""Kafka event publisher with aiokafka and sync fallback."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

from gie_contracts.events import EventEnvelope
from gie_observability.logging import get_logger

from context_intelligence.domain.ports import EventPublisher
from context_intelligence.settings import Settings, get_settings

logger = get_logger(__name__)


class KafkaEventPublisher(EventPublisher):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._producer: Any = None
        self._sync_producer: Any = None
        self._lock = threading.Lock()
        self._use_sync = False

    async def _ensure_async_producer(self) -> Any:
        if self._producer is not None:
            return self._producer
        try:
            from aiokafka import AIOKafkaProducer

            producer = AIOKafkaProducer(
                bootstrap_servers=self._settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await producer.start()
            self._producer = producer
            return producer
        except Exception as exc:
            logger.warning("aiokafka_unavailable", error=str(exc))
            self._use_sync = True
            return None

    def _ensure_sync_producer(self) -> Any:
        with self._lock:
            if self._sync_producer is not None:
                return self._sync_producer
            try:
                from confluent_kafka import Producer

                self._sync_producer = Producer(
                    {"bootstrap.servers": self._settings.kafka_bootstrap_servers}
                )
                return self._sync_producer
            except Exception as exc:
                logger.warning("confluent_kafka_unavailable", error=str(exc))
                return None

    async def publish(self, topic: str, event: EventEnvelope) -> None:
        payload = event.model_dump(mode="json")
        if not self._use_sync:
            producer = await self._ensure_async_producer()
            if producer is not None:
                try:
                    await producer.send_and_wait(topic, payload)
                    return
                except Exception as exc:
                    logger.warning("aiokafka_publish_failed", error=str(exc))
                    self._use_sync = True

        sync_producer = self._ensure_sync_producer()
        if sync_producer is not None:
            try:
                sync_producer.produce(topic, json.dumps(payload).encode("utf-8"))
                sync_producer.poll(0)
                sync_producer.flush(5)
                return
            except Exception as exc:
                logger.warning("sync_kafka_publish_failed", error=str(exc))

        logger.info("kafka_fallback_log_only", topic=topic, event_type=event.event_type, payload=payload)

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None


async def run_publisher_loop(publisher: KafkaEventPublisher) -> None:
    """Keep async producer warm."""
    await publisher._ensure_async_producer()
    while True:
        await asyncio.sleep(3600)
