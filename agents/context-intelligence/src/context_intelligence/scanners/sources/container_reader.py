"""Container image source reader."""

from __future__ import annotations

import json
from pathlib import Path

from gie_contracts.sources import ContainerSource, ScanSource, SourceType

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    command_available,
    run_command,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace


class ContainerUnavailableError(SourceMaterializationError):
    """Docker/runtime not available — caller may skip cleanly."""


@DEFAULT_READER_REGISTRY.register_reader(SourceType.CONTAINER)
class ContainerReader(SourceReader):
    source_types = frozenset({SourceType.CONTAINER})

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not isinstance(source, ContainerSource):
            raise SourceMaterializationError("Expected ContainerSource")

        runtime = source.runtime
        if runtime == "docker" and not command_available("docker"):
            raise ContainerUnavailableError("docker not available")
        if runtime == "podman" and not command_available("podman"):
            raise ContainerUnavailableError("podman not available")

        cmd = "docker" if runtime == "docker" else "podman" if runtime == "podman" else "docker"
        workspace = MaterializedWorkspace.create(prefix="gie-container-")
        root = workspace.path / "rootfs"
        root.mkdir(parents=True, exist_ok=True)

        inspect = run_command([cmd, "inspect", source.image], timeout=60)
        if inspect.returncode == 0:
            (workspace.path / "inspect.json").write_text(inspect.stdout, encoding="utf-8")
            await _export_filesystem(cmd, source.image, root)
        else:
            save_path = workspace.path / "image.tar"
            save = run_command([cmd, "save", "-o", str(save_path), source.image], timeout=300)
            if save.returncode != 0:
                raise SourceMaterializationError(
                    f"container inspect/save failed: {save.stderr.strip() or inspect.stderr.strip()}"
                )
            extract = run_command(["tar", "-xf", str(save_path), "-C", str(workspace.path)], timeout=300)
            if extract.returncode != 0:
                raise SourceMaterializationError(f"tar extract failed: {extract.stderr.strip()}")

        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace


async def _export_filesystem(cmd: str, image: str, root: Path) -> None:
    import subprocess

    container_name = f"gie-export-{root.parent.name[:12]}"
    create = run_command([cmd, "create", "--name", container_name, image], timeout=120)
    if create.returncode != 0:
        return
    tar_path = root.parent / "container.tar"
    try:
        with tar_path.open("wb") as handle:
            proc = subprocess.run(
                [cmd, "export", container_name],
                stdout=handle,
                stderr=subprocess.PIPE,
                timeout=300,
                check=False,
            )
        if proc.returncode == 0 and tar_path.exists():
            run_command(["tar", "-xf", str(tar_path), "-C", str(root)], timeout=300)
    finally:
        run_command([cmd, "rm", "-f", container_name], timeout=30)
