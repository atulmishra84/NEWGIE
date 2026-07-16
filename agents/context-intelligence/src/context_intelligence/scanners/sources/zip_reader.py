"""Zip archive source reader with zip-slip protection."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import httpx

from gie_contracts.sources import ScanSource, SourceType, ZipSource

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    safe_extract_member,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace


@DEFAULT_READER_REGISTRY.register_reader(SourceType.ZIP)
class ZipReader(SourceReader):
    source_types = frozenset({SourceType.ZIP})

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not isinstance(source, ZipSource):
            raise SourceMaterializationError("Expected ZipSource")

        workspace = MaterializedWorkspace.create(prefix="gie-zip-")
        extract_root = workspace.path / "extracted"
        extract_root.mkdir(parents=True, exist_ok=True)

        data = await _load_zip_bytes(source)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                target = safe_extract_member(extract_root, info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as dst:
                    content = src.read()
                    workspace.track_file(len(content))
                    dst.write(content)

        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace


async def _load_zip_bytes(source: ZipSource) -> bytes:
    if source.path:
        path = Path(source.path).expanduser()
        if not path.is_file():
            raise SourceMaterializationError(f"Zip file not found: {path}")
        return path.read_bytes()

    if source.object_uri:
        if source.object_uri.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(source.object_uri)
                response.raise_for_status()
                return response.content
        path = Path(source.object_uri)
        if path.is_file():
            return path.read_bytes()
        raise SourceMaterializationError(f"Unsupported object_uri: {source.object_uri}")

    raise SourceMaterializationError("ZipSource requires path or object_uri")
