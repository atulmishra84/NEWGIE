from __future__ import annotations
from typing import Any
import httpx


class ValidationClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8088",
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

    def validate(
        self,
        bundle: dict[str, Any],
        *,
        persist: bool = True,
        run_simulation: bool = True,
    ) -> dict[str, Any]:
        r = self._client.post(
            "/v1/validate",
            json={
                "bundle": bundle,
                "persist": persist,
                "run_simulation": run_simulation,
            },
        )
        r.raise_for_status()
        return r.json()

    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/simulate", json=payload)
        r.raise_for_status()
        return r.json()

    def get(self, validation_id: str) -> dict[str, Any]:
        r = self._client.get(f"/v1/validation/{validation_id}")
        r.raise_for_status()
        return r.json()

    def report(self, agent_id: str | None = None) -> dict[str, Any]:
        params = {"agent_id": agent_id} if agent_id else None
        r = self._client.get("/v1/validation/report", params=params)
        r.raise_for_status()
        return r.json()
