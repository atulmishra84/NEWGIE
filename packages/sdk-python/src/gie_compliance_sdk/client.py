from __future__ import annotations
from typing import Any
import httpx


class ComplianceClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8084",
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

    def analyze(
        self, bundle: dict[str, Any], *, persist: bool = True
    ) -> dict[str, Any]:
        r = self._client.post(
            "/v1/compliance/analyze", json={"bundle": bundle, "persist": persist}
        )
        r.raise_for_status()
        return r.json()

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/v1/compliance/validate", json=payload)
        r.raise_for_status()
        return r.json()

    def report(self, application_id: str) -> dict[str, Any]:
        r = self._client.get(
            "/v1/compliance/report", params={"application_id": application_id}
        )
        r.raise_for_status()
        return r.json()

    def evidence(
        self, application_id: str, control_id: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"application_id": application_id}
        if control_id:
            params["control_id"] = control_id
        r = self._client.get("/v1/compliance/evidence", params=params)
        r.raise_for_status()
        return r.json()

    def frameworks(self) -> dict[str, Any]:
        r = self._client.get("/frameworks")
        r.raise_for_status()
        return r.json()
