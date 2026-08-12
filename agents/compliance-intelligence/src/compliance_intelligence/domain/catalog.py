"""Load versioned framework/control catalog."""

from __future__ import annotations
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def catalog_path() -> Path:
    env = os.environ.get("GIE_COMPLIANCE_CATALOG_PATH")
    if env and Path(env).exists():
        return Path(env)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "data" / "frameworks" / "catalog_v1.json",
        Path.cwd() / "data" / "frameworks" / "catalog_v1.json",
        Path.cwd()
        / "agents"
        / "compliance-intelligence"
        / "data"
        / "frameworks"
        / "catalog_v1.json",
        Path("/app/data/frameworks/catalog_v1.json"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


@lru_cache
def load_catalog() -> dict[str, Any]:
    path = catalog_path()
    return json.loads(path.read_text())


def list_frameworks() -> list[dict[str, Any]]:
    cat = load_catalog()
    out = []
    for fid, meta in cat["frameworks"].items():
        out.append(
            {
                "id": fid,
                "name": meta["name"],
                "version": meta["version"],
                "last_regulatory_update": meta.get("last_update"),
                "control_count": len(meta.get("controls", [])),
                "catalog_version": cat.get("version"),
            }
        )
    return out
