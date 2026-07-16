"""Git clone source reader."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from gie_contracts.sources import GitSource, ScanSource, SourceType

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    command_available,
    run_command,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace


def _inject_token(url: str, token: str | None) -> str:
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return url
    netloc = f"{token}@{parsed.hostname}"
    if parsed.port:
        netloc = f"{token}@{parsed.hostname}:{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


@DEFAULT_READER_REGISTRY.register_reader(SourceType.GIT)
class GitReader(SourceReader):
    source_types = frozenset({SourceType.GIT})

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not isinstance(source, GitSource):
            raise SourceMaterializationError("Expected GitSource")

        workspace = MaterializedWorkspace.create(prefix="gie-git-")
        clone_dir = workspace.path / "repo"
        clone_dir.mkdir(parents=True, exist_ok=True)

        token = os.environ.get(source.token_secret_ref or "")
        url = _inject_token(source.url, token or None)
        depth = max(1, source.depth)

        if _gitpython_available():
            await _clone_gitpython(url, clone_dir, source.ref, depth)
        elif command_available("git"):
            result = run_command(
                [
                    "git",
                    "clone",
                    "--depth",
                    str(depth),
                    "--branch",
                    source.ref if source.ref != "HEAD" else "main",
                    url,
                    str(clone_dir),
                ],
                timeout=180,
            )
            if result.returncode != 0:
                result = run_command(
                    ["git", "clone", "--depth", str(depth), url, str(clone_dir)],
                    timeout=180,
                )
                if result.returncode != 0:
                    raise SourceMaterializationError(
                        f"git clone failed: {result.stderr.strip() or result.stdout.strip()}"
                    )
                if source.ref and source.ref != "HEAD":
                    checkout = run_command(
                        ["git", "checkout", source.ref],
                        cwd=clone_dir,
                        timeout=60,
                    )
                    if checkout.returncode != 0:
                        raise SourceMaterializationError(
                            f"git checkout failed: {checkout.stderr.strip()}"
                        )
        else:
            raise SourceMaterializationError("git is not available")

        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace


def _gitpython_available() -> bool:
    try:
        import git  # noqa: F401

        return True
    except ImportError:
        return False


async def _clone_gitpython(url: str, dest: Path, ref: str, depth: int) -> None:
    import git

    repo = git.Repo.clone_from(url, dest, depth=depth, branch=None if ref == "HEAD" else ref)
    if ref and ref != "HEAD":
        try:
            repo.git.checkout(ref)
        except git.GitCommandError as exc:
            raise SourceMaterializationError(f"git checkout failed: {exc}") from exc
