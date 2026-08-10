from __future__ import annotations
from typing import Any
import httpx


class ExplainabilityClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8087",
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

    def explain(
        self, bundle: dict[str, Any], *, persist: bool = True
    ) -> dict[str, Any]:
        r = self._client.post(
            "/v1/explain", json={"bundle": bundle, "persist": persist}
        )
        r.raise_for_status()
        return r.json()

    def get(self, explanation_id: str) -> dict[str, Any]:
        r = self._client.get(f"/v1/explanation/{explanation_id}")
        r.raise_for_status()
        return r.json()

    def reasoning_path(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/reasoning/path", json=payload)
        r.raise_for_status()
        return r.json()

    def figma_generate_diagram(
        self, explanation_id: str | None = None
    ) -> dict[str, Any]:
        params = {"explanation_id": explanation_id} if explanation_id else None
        r = self._client.get("/v1/figma-generate-diagram", params=params)
        r.raise_for_status()
        return r.json()
