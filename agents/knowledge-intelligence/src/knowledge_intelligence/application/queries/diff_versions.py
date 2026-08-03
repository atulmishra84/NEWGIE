from __future__ import annotations

from knowledge_intelligence.domain.ports import VersionRepository


class DiffVersionsHandler:
    def __init__(self, versions: VersionRepository) -> None:
        self._versions = versions

    async def handle(self, from_version: str, to_version: str):
        return await self._versions.diff(from_version, to_version)
