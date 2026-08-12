"""Celery tasks for async reindex / ingest."""

from __future__ import annotations

import asyncio

from knowledge_intelligence.infrastructure.celery_app import app


@app.task(name="knowledge.reindex")
def reindex_task(domain: str | None = None) -> dict:
    from knowledge_intelligence.application.di import get_container

    container = get_container()
    return asyncio.get_event_loop().run_until_complete(
        container.reindex.handle(domain=domain)
    )
