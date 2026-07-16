"""MCP server exposing Context Intelligence tools."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from mcp.server.fastmcp import FastMCP
from pydantic import TypeAdapter

from gie_contracts.sources import ScanSource
from context_intelligence.infrastructure.celery_app import execute_scan_task
from context_intelligence.infrastructure.messaging.kafka_publisher import KafkaEventPublisher
from context_intelligence.infrastructure.persistence.database import init_db, session_scope
from context_intelligence.infrastructure.persistence.repositories import (
    SqlAlchemyContextRepository,
    SqlAlchemyOutboxWriter,
)
from context_intelligence.domain.scan_executor import request_scan


@mcp.tool()
async def start_scan(
    tenant_id: str,
    source: dict[str, Any],
    requested_by: str = "mcp",
    idempotency_key: str | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Start a context scan for the given source payload."""
    await init_db()
    publisher = KafkaEventPublisher(get_settings())
    correlation_id = uuid4().hex
    try:
        async with session_scope() as session:
            repo = SqlAlchemyContextRepository(session)
            outbox = SqlAlchemyOutboxWriter(session)
            from gie_contracts.sources import ScanSource

            parsed_source = TypeAdapter(ScanSource).validate_python(source)
            record = await request_scan(
                repo,
                outbox,
                publisher,
                tenant_id=tenant_id,
                source=parsed_source,
                requested_by=requested_by,
                idempotency_key=idempotency_key or uuid4().hex,
                correlation_id=correlation_id,
                webhook_url=webhook_url,
            )
            execute_scan_task.delay(record["scan_id"], tenant_id, correlation_id)
            return record
    finally:
        await publisher.close()


@mcp.tool()
async def get_context_model(tenant_id: str, model_id: str, version: int | None = None) -> dict[str, Any]:
    """Fetch a context model by ID."""
    await init_db()
    async with session_scope() as session:
        repo = SqlAlchemyContextRepository(session)
        model = await repo.get_context_model(UUID(model_id), tenant_id, version=version)
        if not model:
            return {"error": "not_found"}
        return model.model_dump(mode="json")


@mcp.tool()
async def list_findings(
    tenant_id: str,
    scan_id: str | None = None,
    model_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List findings for a scan or model."""
    await init_db()
    async with session_scope() as session:
        repo = SqlAlchemyContextRepository(session)
        items = await repo.list_findings(
            tenant_id=tenant_id,
            scan_id=UUID(scan_id) if scan_id else None,
            model_id=UUID(model_id) if model_id else None,
            limit=limit,
        )
        return {"items": items}


@mcp.tool()
async def diff_models(
    tenant_id: str,
    model_id: str,
    from_version: int,
    to_version: int,
) -> dict[str, Any]:
    """Diff two versions of a context model."""
    await init_db()
    async with session_scope() as session:
        repo = SqlAlchemyContextRepository(session)
        return await repo.diff_models(UUID(model_id), tenant_id, from_version, to_version)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
