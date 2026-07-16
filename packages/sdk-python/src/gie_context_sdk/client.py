"""HTTP client for GIE Context Intelligence API."""

from __future__ import annotations

from typing import Any

import httpx

from gie_context_sdk.models import ModelsClient
from gie_context_sdk.scans import ScansClient


class GieContextClient:
    """Top-level SDK client with scans and models sub-clients."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        *,
        api_key: str | None = None,
        bearer_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        elif bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        self._client = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout)
        self.scans = ScansClient(self._client)
        self.models = ModelsClient(self._client)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GieContextClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
