"""Kafka command listener for knowledge.reindex.requested etc."""

from __future__ import annotations

import asyncio
import json

from gie_observability.logging import get_logger

from knowledge_intelligence.application.di import get_container
from knowledge_intelligence.settings import get_settings

logger = get_logger(__name__)


async def run_listener() -> None:
    settings = get_settings()
    try:
        from aiokafka import AIOKafkaConsumer
    except ImportError:
        logger.error("aiokafka_missing")
        return
    consumer = AIOKafkaConsumer(
        settings.kafka_topic_commands,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="knowledge-intelligence",
        enable_auto_commit=True,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = json.loads(msg.value.decode())
            et = event.get("event_type")
            logger.info("knowledge_command_received", event_type=et)
            container = get_container()
            if et == "knowledge.reindex.requested":
                domains = event.get("domains") or []
                domain = domains[0] if domains else None
                await container.reindex.handle(domain=domain)
    finally:
        await consumer.stop()


def main() -> None:
    asyncio.run(run_listener())


if __name__ == "__main__":
    main()
