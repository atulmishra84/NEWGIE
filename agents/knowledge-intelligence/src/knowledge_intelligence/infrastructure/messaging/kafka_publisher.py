"""Kafka event publisher with graceful no-op fallback."""

from __future__ import annotations

import json
from typing import Any

from gie_observability.logging import get_logger

from knowledge_intelligence.domain.ports import EventPublisher

logger = get_logger(__name__)


class KafkaEventPublisher(EventPublisher):
    def __init__(self, bootstrap: str) -> None:
        self._bootstrap = bootstrap
        self._producer = None

    async def _ensure(self):
        if self._producer is not None:
            return
        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap)
            await self._producer.start()
        except Exception as exc:
            logger.warning("kafka_unavailable", error=str(exc))
            self._producer = False  # type: ignore

    async def publish(self, topic: str, event: dict[str, Any], key: str | None = None) -> None:
        await self._ensure()
        if not self._producer:
            logger.info("kafka_event_dropped", topic=topic, event_type=event.get("event_type"))
            return
        data = json.dumps(event).encode()
        k = key.encode() if key else None
        await self._producer.send_and_wait(topic, data, key=k)

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
