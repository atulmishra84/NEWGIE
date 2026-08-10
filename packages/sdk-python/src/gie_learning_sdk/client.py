from __future__ import annotations
from typing import Any
import httpx


class LearningClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8089",
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

    def feedback(
        self, event: dict[str, Any], *, persist: bool = True
    ) -> dict[str, Any]:
        r = self._client.post("/v1/feedback", json={"event": event, "persist": persist})
        r.raise_for_status()
        return r.json()

    def learn(self, bundle: dict[str, Any], *, persist: bool = True) -> dict[str, Any]:
        r = self._client.post("/v1/learn", json={"bundle": bundle, "persist": persist})
        r.raise_for_status()
        return r.json()

    def history(self, agent_id: str | None = None) -> dict[str, Any]:
        params = {"agent_id": agent_id} if agent_id else None
        r = self._client.get("/v1/learning/history", params=params)
        r.raise_for_status()
        return r.json()

    def knowledge_changes(self, status: str | None = None) -> dict[str, Any]:
        params = {"status": status} if status else None
        r = self._client.get("/v1/knowledge/changes", params=params)
        r.raise_for_status()
        return r.json()
