from __future__ import annotations
from typing import Any
import httpx


class PolicyGeneratorClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8086",
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

    def generate(
        self, bundle: dict[str, Any], *, persist: bool = True
    ) -> dict[str, Any]:
        r = self._client.post(
            "/v1/policy/generate", json={"bundle": bundle, "persist": persist}
        )
        r.raise_for_status()
        return r.json()

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/policy/validate", json=payload)
        r.raise_for_status()
        return r.json()

    def templates(self) -> dict[str, Any]:
        r = self._client.get("/v1/policy/templates")
        r.raise_for_status()
        return r.json()

    def get(self, policy_id: str) -> dict[str, Any]:
        r = self._client.get(f"/v1/policy/{policy_id}")
        r.raise_for_status()
        return r.json()
