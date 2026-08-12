"""Running process source reader (POSIX)."""

from __future__ import annotations

import json
import platform
from pathlib import Path

from gie_contracts.sources import ProcessSource, ScanSource, SourceType

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    copy_tree,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace


@DEFAULT_READER_REGISTRY.register_reader(SourceType.PROCESS)
class ProcessReader(SourceReader):
    source_types = frozenset({SourceType.PROCESS})

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not isinstance(source, ProcessSource):
            raise SourceMaterializationError("Expected ProcessSource")
        if platform.system() == "Windows":
            raise SourceMaterializationError("ProcessReader requires POSIX /proc")

        proc_root = Path(f"/proc/{source.pid}")
        if not proc_root.exists():
            raise SourceMaterializationError(f"Process {source.pid} not found")

        workspace = MaterializedWorkspace.create(prefix="gie-process-")
        meta: dict[str, object] = {"pid": source.pid, "host": source.host}

        cwd_link = proc_root / "cwd"
        if cwd_link.exists():
            cwd = cwd_link.resolve()
            meta["cwd"] = str(cwd)
            if cwd.is_dir():
                target = workspace.path / "cwd"
                copy_tree(cwd, target, workspace=workspace, use_symlinks=True)

        environ = _read_proc_environ(proc_root / "environ")
        meta["environ"] = _heuristic_env(environ)
        (workspace.path / "process.json").write_text(
            json.dumps(meta, indent=2),
            encoding="utf-8",
        )

        cmdline_path = proc_root / "cmdline"
        if cmdline_path.exists():
            raw = (
                cmdline_path.read_bytes()
                .replace(b"\x00", b" ")
                .decode("utf-8", errors="replace")
            )
            (workspace.path / "cmdline.txt").write_text(raw.strip(), encoding="utf-8")

        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace


def _read_proc_environ(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    raw = path.read_bytes()
    items: dict[str, str] = {}
    for part in raw.split(b"\x00"):
        if b"=" not in part:
            continue
        key, _, value = part.partition(b"=")
        try:
            items[key.decode()] = value.decode(errors="replace")
        except UnicodeDecodeError:
            continue
    return items


def _heuristic_env(environ: dict[str, str]) -> dict[str, str]:
    keys_of_interest = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AWS_REGION",
        "GOOGLE_CLOUD_PROJECT",
        "KUBECONFIG",
        "LANGCHAIN_TRACING_V2",
        "VIRTUAL_ENV",
        "CONDA_DEFAULT_ENV",
        "NODE_ENV",
        "PYTHONPATH",
    )
    redacted: dict[str, str] = {}
    for key in keys_of_interest:
        if key in environ:
            value = environ[key]
            if "KEY" in key or "SECRET" in key or "TOKEN" in key:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = value
    return redacted
