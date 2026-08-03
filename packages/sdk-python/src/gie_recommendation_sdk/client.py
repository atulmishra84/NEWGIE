from __future__ import annotations
from typing import Any
import httpx

class RecommendationClient:
    def __init__(self, base_url: str = "http://localhost:8085", token: str | None = None, api_key: str | None = None):
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=60.0)

    def generate(self, bundle: dict[str, Any], *, persist: bool = True) -> dict[str, Any]:
        r = self._client.post("/v1/recommendations", json={"bundle": bundle, "persist": persist})
        r.raise_for_status()
        return r.json()

    def get(self, agent_id: str) -> dict[str, Any]:
        r = self._client.get(f"/v1/recommendations/{agent_id}")
        r.raise_for_status()
        return r.json()

    def history(self, agent_id: str | None = None) -> dict[str, Any]:
        params = {"agent_id": agent_id} if agent_id else None
        r = self._client.get("/v1/recommendations/history", params=params)
        r.raise_for_status()
        return r.json()

    def approve(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/recommendations/approve", json=payload)
        r.raise_for_status()
        return r.json()
