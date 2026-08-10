from __future__ import annotations

from typing import Any

import httpx


class PolicyClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8082",
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

    def generate(self, bundle: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        r = self._client.post(
            "/v1/policies/generate", json={"bundle": bundle, "dry_run": dry_run}
        )
        r.raise_for_status()
        return r.json()

    def explain(
        self, decision_id: str, guardrail_id: str | None = None
    ) -> dict[str, Any]:
        params = {"guardrail_id": guardrail_id} if guardrail_id else None
        r = self._client.get(
            f"/v1/policies/decisions/{decision_id}/explain", params=params
        )
        r.raise_for_status()
        return r.json()
