from __future__ import annotations
import asyncio, json
from gie_observability.logging import get_logger
from risk_intelligence.settings import get_settings

logger = get_logger(__name__)

async def run_listener() -> None:
    settings = get_settings()
    try:
        from aiokafka import AIOKafkaConsumer
    except ImportError:
        return
    consumer = AIOKafkaConsumer(settings.kafka_topic_commands, bootstrap_servers=settings.kafka_bootstrap_servers, group_id="risk-intelligence")
    await consumer.start()
    try:
        async for msg in consumer:
            event = json.loads(msg.value.decode())
            logger.info("risk_command_received", event_type=event.get("event_type"))
    finally:
        await consumer.stop()
