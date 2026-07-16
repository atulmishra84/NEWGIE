"""Context models API client."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from gie_contracts.context_model import ContextModel


class ModelsClient:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def get(self, model_id: UUID | str, *, version: int | None = None) -> ContextModel:
        params = {"version": version} if version is not None else None
        resp = self._client.get(f"/v1/context-models/{model_id}", params=params)
        resp.raise_for_status()
        return ContextModel.model_validate(resp.json()["data"])

    def list_versions(self, model_id: UUID | str) -> dict[str, Any]:
        resp = self._client.get(f"/v1/context-models/{model_id}/versions")
        resp.raise_for_status()
        return resp.json()["data"]

    def diff(self, model_id: UUID | str, from_version: int, to_version: int) -> dict[str, Any]:
        resp = self._client.get(
            f"/v1/context-models/{model_id}/diff",
            params={"from": from_version, "to": to_version},
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def list_findings(self, model_id: UUID | str, *, limit: int = 100) -> dict[str, Any]:
        resp = self._client.get(f"/v1/context-models/{model_id}/findings", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()["data"]
