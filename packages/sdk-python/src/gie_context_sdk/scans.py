"""Scans API client."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from gie_contracts.sources import ScanSource


class ScansClient:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def create(
        self,
        source: ScanSource | dict[str, Any],
        *,
        idempotency_key: str | None = None,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source": source.model_dump(mode="json")
            if hasattr(source, "model_dump")
            else source,
        }
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        if webhook_url:
            payload["webhook_url"] = webhook_url
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        resp = self._client.post("/v1/scans", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["data"]

    def get(self, scan_id: UUID | str) -> dict[str, Any]:
        resp = self._client.get(f"/v1/scans/{scan_id}")
        resp.raise_for_status()
        return resp.json()["data"]

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        resp = self._client.get("/v1/scans", params=params)
        resp.raise_for_status()
        return resp.json()["data"]

    def cancel(self, scan_id: UUID | str) -> dict[str, Any]:
        resp = self._client.post(f"/v1/scans/{scan_id}/cancel")
        resp.raise_for_status()
        return resp.json()["data"]
