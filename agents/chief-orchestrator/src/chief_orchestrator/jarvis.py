"""Optional JARVIS integration bridge (webhook forward + config)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from chief_orchestrator.config import settings


def _config_path() -> Path:
    root = Path(settings.artifact_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root / "jarvis-config.json"


def load_config() -> dict[str, Any]:
    path = _config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {
                    "enabled": bool(data.get("enabled", False)),
                    "webhook_url": str(data.get("webhook_url") or settings.jarvis_webhook_url or ""),
                    "token": str(data.get("token") or settings.jarvis_token or ""),
                }
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "enabled": bool(settings.jarvis_enabled),
        "webhook_url": settings.jarvis_webhook_url,
        "token": settings.jarvis_token,
    }


def save_config(*, enabled: bool, webhook_url: str = "", token: str = "") -> dict[str, Any]:
    cfg = {
        "enabled": enabled,
        "webhook_url": webhook_url.strip(),
        "token": token.strip(),
    }
    path = _config_path()
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    return {
        "enabled": cfg["enabled"],
        "webhook_url": cfg["webhook_url"],
        "token_set": bool(cfg["token"]),
    }


def public_config() -> dict[str, Any]:
    cfg = load_config()
    return {
        "enabled": cfg["enabled"],
        "webhook_url": cfg["webhook_url"],
        "token_set": bool(cfg.get("token")),
        "bridge": "gie-jarvis",
    }


async def forward_event(event: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"forwarded": False, "reason": "jarvis_disabled"}
    webhook = (cfg.get("webhook_url") or "").strip()
    if not webhook:
        return {"forwarded": False, "reason": "missing_webhook_url"}

    headers = {"Content-Type": "application/json", "X-GIE-Source": "chief-orchestrator"}
    token = (cfg.get("token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook, json=event, headers=headers)
            return {
                "forwarded": True,
                "status_code": resp.status_code,
                "ok": 200 <= resp.status_code < 300,
            }
    except httpx.HTTPError as exc:
        return {
            "forwarded": False,
            "reason": "webhook_error",
            "error": str(exc),
        }
