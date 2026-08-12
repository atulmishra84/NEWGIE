"""GitHub repository source reader."""

from __future__ import annotations

import os

from gie_contracts.sources import GitHubSource, GitSource, ScanSource, SourceType

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
)
from context_intelligence.scanners.sources.git_reader import GitReader
from context_intelligence.scanners.workspace import MaterializedWorkspace


@DEFAULT_READER_REGISTRY.register_reader(SourceType.GITHUB)
class GitHubReader(SourceReader):
    source_types = frozenset({SourceType.GITHUB})

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not isinstance(source, GitHubSource):
            raise SourceMaterializationError("Expected GitHubSource")

        token = os.environ.get(source.token_secret_ref or "GITHUB_TOKEN") or None
        url = f"https://github.com/{source.owner}/{source.repo}.git"
        if token:
            url = f"https://{token}@github.com/{source.owner}/{source.repo}.git"

        git_source = GitSource(
            url=url,
            ref=source.ref,
            depth=1,
            labels=dict(source.labels),
        )
        return await GitReader().materialize(git_source)
