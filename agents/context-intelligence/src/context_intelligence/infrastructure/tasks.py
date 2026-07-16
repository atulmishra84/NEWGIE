"""Async scan tasks."""

from __future__ import annotations

from uuid import UUID

from context_intelligence.application.scan_service import scan_folder
from context_intelligence.infrastructure.celery_app import app


@app.task(name="context.scan.folder", bind=True, max_retries=3)
def scan_folder_task(self, path: str, tenant_id: str, scan_id: str) -> dict:
    model = scan_folder(path, tenant_id=tenant_id, scan_id=UUID(scan_id))
    return model.model_dump(mode="json")
