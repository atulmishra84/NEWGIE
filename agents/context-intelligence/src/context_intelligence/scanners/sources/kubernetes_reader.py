"""Kubernetes cluster source reader."""

from __future__ import annotations

import json
import os
from pathlib import Path

from gie_contracts.sources import KubernetesSource, ScanSource, SourceType

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    command_available,
    run_command,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace


class KubernetesUnavailableError(SourceMaterializationError):
    """kubectl or kubeconfig not available."""


@DEFAULT_READER_REGISTRY.register_reader(SourceType.KUBERNETES)
class KubernetesReader(SourceReader):
    source_types = frozenset({SourceType.KUBERNETES})

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not isinstance(source, KubernetesSource):
            raise SourceMaterializationError("Expected KubernetesSource")

        if not command_available("kubectl"):
            raise KubernetesUnavailableError("kubectl not available")
        if not _kubeconfig_present():
            raise KubernetesUnavailableError("kubeconfig not present")

        workspace = MaterializedWorkspace.create(prefix="gie-k8s-")
        out_dir = workspace.path / "cluster"
        out_dir.mkdir(parents=True, exist_ok=True)

        ns = source.namespace
        label_selector = ",".join(f"{k}={v}" for k, v in source.selectors.items())
        ctx_args: list[str] = ["--context", source.context] if source.context else []

        kinds = ("pods", "deployments", "services", "configmaps")
        for kind in kinds:
            cmd = ["kubectl", *ctx_args, "get", kind, "-n", ns]
            if label_selector:
                cmd.extend(["-l", label_selector])
            cmd.extend(["-o", "json"])
            result = run_command(cmd, timeout=120)
            payload = (
                result.stdout
                if result.returncode == 0
                else json.dumps({"error": result.stderr.strip()})
            )
            (out_dir / f"{kind}.json").write_text(payload, encoding="utf-8")

        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace


def _kubeconfig_present() -> bool:
    if os.environ.get("KUBECONFIG"):
        for part in os.environ["KUBECONFIG"].split(os.pathsep):
            if Path(part).expanduser().exists():
                return True
    return (Path.home() / ".kube" / "config").exists()
