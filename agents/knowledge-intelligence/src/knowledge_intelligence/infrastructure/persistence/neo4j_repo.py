"""Neo4j knowledge graph projection."""

from __future__ import annotations

from typing import Any

from gie_contracts.knowledge import KnowledgeEdge, KnowledgeNode
from neo4j import AsyncGraphDatabase

from knowledge_intelligence.domain.ports import GraphRepository
from knowledge_intelligence.settings import Settings


class Neo4jKnowledgeGraph(GraphRepository):
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    @classmethod
    def from_settings(cls, settings: Settings) -> "Neo4jKnowledgeGraph":
        return cls(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    async def project_nodes(self, nodes: list[KnowledgeNode]) -> None:
        async with self._driver.session() as session:
            for n in nodes:
                await session.run(
                    """
                    MERGE (x:KnowledgeNode {node_id: $id})
                    SET x.kind=$kind, x.domain=$domain, x.title=$title, x.version=$version, x.active=$active
                    """,
                    id=n.node_id,
                    kind=n.kind.value,
                    domain=n.domain.value,
                    title=n.title,
                    version=n.version,
                    active=n.active,
                )

    async def project_edges(self, edges: list[KnowledgeEdge]) -> None:
        async with self._driver.session() as session:
            for e in edges:
                await session.run(
                    f"""
                    MATCH (a:KnowledgeNode {{node_id: $src}})
                    MATCH (b:KnowledgeNode {{node_id: $tgt}})
                    MERGE (a)-[r:{e.relationship.value} {{edge_id: $eid}}]->(b)
                    SET r.weight=$weight, r.version=$version
                    """,
                    src=e.source_id,
                    tgt=e.target_id,
                    eid=e.edge_id,
                    weight=e.weight,
                    version=e.version,
                )

    async def shortest_paths(
        self, source_id: str, target_id: str, max_depth: int = 4
    ) -> list[list[str]]:
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH p = shortestPath(
                  (a:KnowledgeNode {node_id: $src})-[*..%d]-(b:KnowledgeNode {node_id: $tgt})
                )
                RETURN [n IN nodes(p) | n.node_id] AS path
                LIMIT 5
                """
                % max_depth,
                src=source_id,
                tgt=target_id,
            )
            paths = []
            async for record in result:
                paths.append(list(record["path"]))
            return paths

    async def expand(
        self, node_ids: list[str], hops: int = 1
    ) -> tuple[list[str], list[dict[str, Any]]]:
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (n:KnowledgeNode)-[*1..%d]-(m:KnowledgeNode)
                WHERE n.node_id IN $ids AND NOT m.node_id IN $ids
                RETURN DISTINCT m.node_id AS id, m.title AS title, m.kind AS kind, m.domain AS domain
                LIMIT 50
                """
                % hops,
                ids=node_ids,
            )
            rows = []
            ids = []
            async for record in result:
                ids.append(record["id"])
                rows.append(
                    {
                        "id": record["id"],
                        "title": record["title"],
                        "kind": record["kind"],
                        "domain": record["domain"],
                    }
                )
            return ids, rows

    async def ping(self) -> bool:
        try:
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._driver.close()
