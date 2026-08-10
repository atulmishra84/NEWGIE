"""Simulated / HTTP agent invoker."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import httpx

from gie_contracts.orchestrator import AgentId
from orchestrator.domain.demo_fixtures import demo_payload, is_demo_request
from orchestrator.domain.live_invoke import live_invoke_agent
from orchestrator.domain.retry import RetryableError
from orchestrator.domain.router import agent_base_urls
from orchestrator.settings import Settings


class SimulatedAgentInvoker:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._fail_once: set[str] = set()

    def arm_transient_failure(self, agent_id: str) -> None:
        self._fail_once.add(agent_id)

    async def invoke(
        self, agent_id: str, version: str, payload: dict[str, Any], *, timeout_ms: int
    ) -> dict[str, Any]:
        if agent_id in self._fail_once:
            self._fail_once.discard(agent_id)
            raise RetryableError(f"{agent_id} temporarily unavailable")
        await asyncio.sleep(min(0.005, timeout_ms / 1_000_000))
        if is_demo_request(payload.get("input") or payload):
            # Simulated mode still returns rich fixtures for local UX demos
            merged = {**payload, **(payload.get("input") or {})}
            return demo_payload(agent_id, version, merged)
        return {
            "agent_id": agent_id,
            "version": version,
            "status": "ok",
            "summary": f"{agent_id} analysis complete",
            "artifacts": {"id": uuid4().hex[:12]},
            "echo": {
                "tenant_id": payload.get("tenant_id"),
                "keys": list(payload.keys())[:12],
            },
            "confidence": 0.85,
            "live": False,
        }

    async def health(self) -> list[dict[str, Any]]:
        from orchestrator.domain.router import default_health

        return [e.model_dump(mode="json") for e in default_health(self._settings)]


class HttpAgentInvoker:
    """Calls live peer business APIs (not just /healthz)."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._urls = agent_base_urls(settings)

    def _demo_payload_view(self, payload: dict[str, Any]) -> dict[str, Any]:
        inp = payload.get("input") or {}
        return {
            "tenant_id": payload.get("tenant_id"),
            "source": inp.get("source") or {},
            "options": inp.get("options") or {},
            "metadata": inp.get("metadata") or {},
            **inp,
        }

    async def invoke(
        self, agent_id: str, version: str, payload: dict[str, Any], *, timeout_ms: int
    ) -> dict[str, Any]:
        aid = AgentId(agent_id)
        base = self._urls[aid]
        demo_view = self._demo_payload_view(payload)

        try:
            return await live_invoke_agent(
                agent_id=agent_id,
                version=version,
                base_url=base,
                payload=payload,
                settings=self._settings,
                timeout_ms=timeout_ms,
            )
        except RetryableError:
            raise
        except Exception as exc:  # noqa: BLE001
            # Demo scenarios keep a readable brief if a peer contract fails.
            if is_demo_request(demo_view):
                out = demo_payload(agent_id, version, demo_view)
                out["peer_base_url"] = base
                out["peer_healthy"] = True
                out["live"] = False
                out["live_fallback"] = True
                out["live_error"] = str(exc)[:300]
                return out
            # Non-demo: surface a structured failure the engine can mark failed/retry
            raise RetryableError(f"{agent_id} live invoke failed: {exc}") from exc

    async def health(self) -> list[dict[str, Any]]:
        results = []
        async with httpx.AsyncClient(timeout=2.0) as client:
            for agent_id, url in self._urls.items():
                healthy = False
                latency = 0.0
                try:
                    r = await client.get(f"{url}/healthz")
                    healthy = r.status_code < 500
                    latency = float(r.elapsed.total_seconds() * 1000.0)
                except Exception:  # noqa: BLE001
                    healthy = False
                results.append(
                    {
                        "agent_id": agent_id.value,
                        "base_url": url,
                        "version": "1.0.0",
                        "healthy": healthy,
                        "latency_ms_p95": round(latency, 1),
                    }
                )
        return results


def build_invoker(settings: Settings):
    if settings.simulate_agents or settings.gie_env in {"test", "local"}:
        return SimulatedAgentInvoker(settings)
    return HttpAgentInvoker(settings)
