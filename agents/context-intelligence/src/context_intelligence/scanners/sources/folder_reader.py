"""Folder source reader."""

from __future__ import annotations

from pathlib import Path

from gie_contracts.sources import FolderSource, ScanSource, SourceType

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    copy_tree,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace


@DEFAULT_READER_REGISTRY.register_reader(SourceType.FOLDER)
class FolderReader(SourceReader):
    source_types = frozenset({SourceType.FOLDER})

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not isinstance(source, FolderSource):
            raise SourceMaterializationError("Expected FolderSource")
        src = Path(source.path).expanduser().resolve()
        if not src.exists() or not src.is_dir():
            raise SourceMaterializationError(f"Folder not found: {src}")

        workspace = MaterializedWorkspace.create(prefix="gie-folder-")
        copy_tree(src, workspace.path, workspace=workspace, use_symlinks=False)
        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace
