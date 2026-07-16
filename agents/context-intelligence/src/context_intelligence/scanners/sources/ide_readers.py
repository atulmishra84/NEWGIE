"""IDE workspace source readers."""

from __future__ import annotations

import json
from pathlib import Path

from gie_contracts.sources import (
    CursorProjectSource,
    FrameworkProjectSource,
    IdeWorkspaceSource,
    ScanSource,
    SourceType,
    VsCodeWorkspaceSource,
)

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    copy_tree,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace

IDE_SOURCE_TYPES = (
    SourceType.IDE_WORKSPACE,
    SourceType.CURSOR_PROJECT,
    SourceType.VSCODE_WORKSPACE,
    SourceType.LANGGRAPH,
    SourceType.OPENAI_AGENTS,
    SourceType.CREWAI,
    SourceType.AUTOGEN,
    SourceType.SEMANTIC_KERNEL,
    SourceType.AZURE_AI_FOUNDRY,
)


@DEFAULT_READER_REGISTRY.register_reader(*IDE_SOURCE_TYPES)
class IdeWorkspaceReader(SourceReader):
    source_types = frozenset(IDE_SOURCE_TYPES)

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        root = _resolve_root(source)
        if not root.exists():
            raise SourceMaterializationError(f"IDE workspace path not found: {root}")

        workspace = MaterializedWorkspace.create(prefix="gie-ide-")
        project_dir = workspace.path / "project"
        copy_tree(root, project_dir, workspace=workspace, use_symlinks=True)

        ide_meta = _collect_ide_metadata(root, source)
        (workspace.path / "ide_metadata.json").write_text(
            json.dumps(ide_meta, indent=2),
            encoding="utf-8",
        )
        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace


def _resolve_root(source: ScanSource) -> Path:
    path: str | None = None
    if isinstance(source, (IdeWorkspaceSource, CursorProjectSource, VsCodeWorkspaceSource)):
        path = source.path
    elif isinstance(source, FrameworkProjectSource):
        path = source.path
    if not path:
        raise SourceMaterializationError("Unsupported IDE/framework source")
    return Path(path).expanduser().resolve()


def _collect_ide_metadata(root: Path, source: ScanSource) -> dict[str, object]:
    meta: dict[str, object] = {"source_type": source.type.value, "root": str(root)}

    cursor_dir = root / ".cursor"
    if cursor_dir.is_dir():
        meta["cursor"] = _snapshot_dir(cursor_dir)

    vscode_dir = root / ".vscode"
    if vscode_dir.is_dir():
        meta["vscode"] = _snapshot_dir(vscode_dir)

    for ws_file in root.glob("*.code-workspace"):
        try:
            meta.setdefault("code_workspaces", []).append(
                {"path": str(ws_file), "content": json.loads(ws_file.read_text(encoding="utf-8"))}
            )
        except (OSError, json.JSONDecodeError):
            meta.setdefault("code_workspaces", []).append({"path": str(ws_file), "error": "unreadable"})

    if isinstance(source, VsCodeWorkspaceSource) and source.workspace_file:
        ws = Path(source.workspace_file).expanduser()
        if ws.is_file():
            meta["primary_workspace_file"] = str(ws)

    if isinstance(source, FrameworkProjectSource):
        meta["framework_hint"] = source.type.value
        meta["extra"] = dict(source.extra)

    return meta


def _snapshot_dir(path: Path) -> dict[str, object]:
    snapshot: dict[str, object] = {"path": str(path), "files": []}
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        rel = item.relative_to(path).as_posix()
        if item.suffix in {".json", ".md", ".yaml", ".yml", ".toml"}:
            try:
                snapshot["files"].append({"path": rel, "size": item.stat().st_size})
            except OSError:
                continue
        elif len(snapshot["files"]) < 200:
            snapshot["files"].append({"path": rel, "size": item.stat().st_size})
    return snapshot
