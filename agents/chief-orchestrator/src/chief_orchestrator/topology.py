"""Multi-region / multi-cluster topology loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from chief_orchestrator.config import settings

_DEFAULT = {
    "version": 1,
    "regions": [
        {
            "id": "us-east-1",
            "name": "US East",
            "clusters": [
                {
                    "id": "staging-use1",
                    "env": "staging",
                    "endpoint": "http://127.0.0.1:8090/demo/golden",
                    "weight": 100,
                },
                {
                    "id": "prod-use1",
                    "env": "production",
                    "endpoint": "http://127.0.0.1:8090/demo/prod/us-east-1",
                    "weight": 70,
                },
            ],
        },
        {
            "id": "eu-west-1",
            "name": "EU West",
            "clusters": [
                {
                    "id": "staging-euw1",
                    "env": "staging",
                    "endpoint": "http://127.0.0.1:8090/demo/golden",
                    "weight": 100,
                },
                {
                    "id": "prod-euw1",
                    "env": "production",
                    "endpoint": "http://127.0.0.1:8090/demo/prod/eu-west-1",
                    "weight": 30,
                },
            ],
        },
    ],
    "promotion": {
        "order": ["us-east-1", "eu-west-1"],
        "require_all_healthy": True,
        "unsupervised_allowed": True,
    },
}


def load_topology() -> dict[str, Any]:
    candidates = [
        Path(settings.multi_region_config),
        Path("deploy/full-gie/multi-region.yaml"),
        Path("/workspace/deploy/full-gie/multi-region.yaml"),
    ]
    for path in candidates:
        if path.is_file():
            data = yaml.safe_load(path.read_text()) or {}
            if isinstance(data, dict) and data.get("regions"):
                return data
    return _DEFAULT


def production_targets(topology: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    topo = topology or load_topology()
    order = list((topo.get("promotion") or {}).get("order") or [])
    regions = {r["id"]: r for r in topo.get("regions", [])}
    targets: list[dict[str, Any]] = []
    for rid in order or list(regions):
        region = regions.get(rid)
        if not region:
            continue
        for cluster in region.get("clusters", []):
            if cluster.get("env") == "production":
                targets.append(
                    {
                        "region": rid,
                        "cluster": cluster["id"],
                        "endpoint": cluster["endpoint"],
                        "weight": cluster.get("weight", 100),
                    }
                )
    return targets


def staging_targets(topology: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    topo = topology or load_topology()
    targets: list[dict[str, Any]] = []
    for region in topo.get("regions", []):
        for cluster in region.get("clusters", []):
            if cluster.get("env") == "staging":
                targets.append(
                    {
                        "region": region["id"],
                        "cluster": cluster["id"],
                        "endpoint": cluster["endpoint"],
                        "weight": cluster.get("weight", 100),
                    }
                )
    return targets
