from __future__ import annotations
from typing import Any
import httpx

class OrchestratorClient:
    def __init__(self, base_url: str = "http://localhost:8091", token: str | None = None, api_key: str | None = None):
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=120.0)

    def analyze(self, request: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/analyze", json=request)
        r.raise_for_status()
        return r.json()

    def workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/workflow", json=request)
        r.raise_for_status()
        return r.json()

    def status(self) -> dict[str, Any]:
        r = self._client.get("/v1/status")
        r.raise_for_status()
        return r.json()

    def execution(self, execution_id: str) -> dict[str, Any]:
        r = self._client.get(f"/v1/execution/{execution_id}")
        r.raise_for_status()
        return r.json()

    def trace(self, trace_id: str) -> dict[str, Any]:
        r = self._client.get(f"/v1/trace/{trace_id}")
        r.raise_for_status()
        return r.json()
