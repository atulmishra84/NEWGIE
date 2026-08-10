"""Python SDK for Knowledge Intelligence Agent."""

from __future__ import annotations

from typing import Any

import httpx


class KnowledgeClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8081",
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

    def query(self, query: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"query": query, **kwargs}
        r = self._client.post("/v1/knowledge/query", json=payload)
        r.raise_for_status()
        return r.json()

    def get_node(self, node_id: str, version: str | None = None) -> dict[str, Any]:
        params = {"version": version} if version else None
        r = self._client.get(f"/v1/knowledge/nodes/{node_id}", params=params)
        r.raise_for_status()
        return r.json()

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/knowledge/nodes", json=payload)
        r.raise_for_status()
        return r.json()

    def diff(self, from_version: str, to_version: str) -> dict[str, Any]:
        r = self._client.get(
            "/v1/knowledge/versions/diff",
            params={"from_version": from_version, "to_version": to_version},
        )
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()
