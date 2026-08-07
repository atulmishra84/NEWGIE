"""Celery application and scan task worker."""

from __future__ import annotations

import asyncio
from uuid import UUID

from celery import Celery
from gie_observability.logging import configure_logging, get_logger

from context_intelligence.domain.scan_executor import ScanExecutor
from context_intelligence.infrastructure.messaging.kafka_publisher import KafkaEventPublisher
from context_intelligence.infrastructure.messaging.webhooks import deliver_webhook
from context_intelligence.infrastructure.persistence.database import init_db, session_scope
from context_intelligence.infrastructure.persistence.neo4j_repo import Neo4jGraphRepository
from context_intelligence.infrastructure.persistence.qdrant_store import QdrantEvidenceVectorStore
from context_intelligence.infrastructure.persistence.repositories import (
    SqlAlchemyContextRepository,
    SqlAlchemyOutboxWriter,
)
from gie_llm import BedrockLLMClient
from context_intelligence.domain.llm_enhancer import enhance_context_model
from context_intelligence.settings import get_settings
from context_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)
settings = get_settings()

app = Celery(
    "context_intelligence",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)
app.conf.task_default_queue = "scans"
app.conf.task_routes = {"context_intelligence.infrastructure.celery_app.execute_scan_task": {"queue": "scans"}}
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _execute_scan_async(scan_id: UUID, tenant_id: str, correlation_id: str) -> dict:
    configure_logging(level=settings.log_level)
    await init_db()
    publisher = KafkaEventPublisher(settings)
    graph = Neo4jGraphRepository.from_settings(settings)
    vectors = QdrantEvidenceVectorStore.from_settings(settings)
    try:
        async with session_scope() as session:
            repo = SqlAlchemyContextRepository(session)
            outbox = SqlAlchemyOutboxWriter(session)
            executor = ScanExecutor(repo, outbox, publisher, graph, vectors, producer_version=AGENT_VERSION)
            model = await executor.execute(scan_id, tenant_id, correlation_id)
            if settings.bedrock_enabled:
                llm = BedrockLLMClient(
                    region=settings.aws_region,
                    model_id=settings.bedrock_model_id,
                    max_tokens=settings.bedrock_max_tokens,
                    temperature=settings.bedrock_temperature,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    aws_session_token=settings.aws_session_token,
                )
                model_dict = model.model_dump(mode="json")
                enhanced = await enhance_context_model(model_dict, client=llm)
                model = model.model_copy(update={"llm_enhancement": {
                    "narrative": enhanced.get("llm_narrative", ""),
                    "key_insights": enhanced.get("llm_key_insights", []),
                    "recommendations": enhanced.get("llm_recommendations", []),
                    "model": enhanced.get("llm_model", ""),
                }})
            scan = await repo.get_scan(scan_id, tenant_id)
            if scan and scan.get("webhook_url"):
                await deliver_webhook(
                    scan["webhook_url"],
                    {
                        "event_type": "context.scan.completed",
                        "scan_id": str(scan_id),
                        "model_id": str(model.model_id),
                        "version": model.version,
                    },
                )
            return {"model_id": str(model.model_id), "version": model.version}
    finally:
        await publisher.close()
        await graph.close()


@app.task(name="context_intelligence.infrastructure.celery_app.execute_scan_task", bind=True, max_retries=3)
def execute_scan_task(self, scan_id: str, tenant_id: str, correlation_id: str) -> dict:
    """Celery task entrypoint for scan execution."""
    logger.info("execute_scan_task_started", scan_id=scan_id, tenant_id=tenant_id)
    try:
        return _run_async(_execute_scan_async(UUID(scan_id), tenant_id, correlation_id))
    except Exception as exc:
        logger.exception("execute_scan_task_failed", scan_id=scan_id)
        raise self.retry(exc=exc, countdown=min(60, 2 ** self.request.retries))
