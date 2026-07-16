"""Shared helpers for source readers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from gie_contracts.sources import ScanSource, SourceType

from context_intelligence.scanners.workspace import (
    MaterializedWorkspace,
    SKIP_DIR_NAMES,
    WorkspaceLimitError,
)


class SourceMaterializationError(Exception):
    """Raised when a source cannot be materialized."""


class SourceReader(ABC):
    """Materializes a scan source into a temporary workspace."""

    source_types: frozenset[SourceType]

    @abstractmethod
    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        raise NotImplementedError

    async def materialize_into(
        self, source: ScanSource, workspace: MaterializedWorkspace
    ) -> str:
        """Ports-compatible adapter: populate an existing workspace, return digest."""
        populated = await self.materialize(source)
        copy_tree(populated.path, workspace.path, workspace=workspace)
        await populated.cleanup()
        return workspace.compute_digest()

    def supports(self, source: ScanSource) -> bool:
        return source.type in self.source_types


def copy_tree(
    src: Path,
    dst: Path,
    *,
    workspace: MaterializedWorkspace | None = None,
    use_symlinks: bool = False,
) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel_root = Path(root).relative_to(src)
        if any(part in SKIP_DIR_NAMES for part in rel_root.parts):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        target_root = dst / rel_root
        target_root.mkdir(parents=True, exist_ok=True)
        for name in files:
            source_file = Path(root) / name
            target_file = target_root / name
            size = source_file.stat().st_size
            if workspace is not None:
                workspace.track_file(size)
            if use_symlinks:
                if target_file.exists() or target_file.is_symlink():
                    target_file.unlink(missing_ok=True)
                target_file.symlink_to(source_file.resolve())
            else:
                shutil.copy2(source_file, target_file)


def digest_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def safe_extract_member(target_dir: Path, member_path: str) -> Path:
    destination = (target_dir / member_path).resolve()
    if not str(destination).startswith(str(target_dir.resolve())):
        raise WorkspaceLimitError(f"Zip slip blocked: {member_path}")
    return destination


def write_metadata(workspace: MaterializedWorkspace, source: ScanSource) -> None:
    meta_dir = workspace.path / ".gie"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "source.json").write_text(
        json.dumps(source.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
