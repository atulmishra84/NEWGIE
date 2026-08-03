from __future__ import annotations

from knowledge_intelligence.application.errors import NotFoundError
from knowledge_intelligence.domain.ports import KnowledgeNodeRepository


class GetNodeHandler:
    def __init__(self, nodes: KnowledgeNodeRepository) -> None:
        self._nodes = nodes

    async def handle(self, node_id: str, version: str | None = None):
        node = await self._nodes.get_node(node_id, version=version)
        if not node:
            raise NotFoundError(f"Node not found: {node_id}")
        return node
