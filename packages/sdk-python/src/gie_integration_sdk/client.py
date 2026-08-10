from __future__ import annotations
from typing import Any
import httpx


class IntegrationClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8090",
        token: str | None = None,
        api_key: str | None = None,
    ):
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), headers=headers, timeout=60.0
        )

    def platforms(self) -> dict[str, Any]:
        r = self._client.get("/v1/integrations")
        r.raise_for_status()
        return r.json()

    def connect(self, request: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/integrations/connect", json=request)
        r.raise_for_status()
        return r.json()

    def sync(
        self,
        connection_id: str,
        payload: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        r = self._client.post(
            f"/v1/integrations/{connection_id}/sync",
            json={"tenant_id": tenant_id, "payload": payload or {}},
        )
        r.raise_for_status()
        return r.json()

    def token(self, request: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/auth/token", json=request)
        r.raise_for_status()
        return r.json()

    def audit(self) -> dict[str, Any]:
        r = self._client.get("/v1/audit")
        r.raise_for_status()
        return r.json()
