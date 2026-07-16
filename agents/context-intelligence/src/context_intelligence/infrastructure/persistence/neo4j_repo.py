"""Neo4j graph projection for ContextModel.graph."""

from __future__ import annotations

from typing import Any

from gie_contracts.context_model import ContextModel
from neo4j import AsyncGraphDatabase, AsyncDriver

from context_intelligence.domain.ports import GraphRepository
from context_intelligence.settings import Settings, get_settings


class Neo4jGraphRepository(GraphRepository):
    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> Neo4jGraphRepository:
        cfg = settings or get_settings()
        driver = AsyncGraphDatabase.driver(
            cfg.neo4j_uri,
            auth=(cfg.neo4j_user, cfg.neo4j_password),
        )
        return cls(driver)

    async def close(self) -> None:
        await self._driver.close()

    async def project_context_model(self, model: ContextModel, tenant_id: str) -> None:
        graph = model.graph
        if not graph.nodes and not graph.edges:
            return

        async with self._driver.session() as session:
            await session.execute_write(
                self._write_graph,
                tenant_id=str(tenant_id),
                model_id=str(model.model_id),
                version=model.version,
                nodes=[n.model_dump(mode="json") for n in graph.nodes],
                edges=[e.model_dump(mode="json") for e in graph.edges],
            )

    @staticmethod
    async def _write_graph(
        tx: Any,
        *,
        tenant_id: str,
        model_id: str,
        version: int,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        await tx.run(
            """
            MERGE (m:ContextModel {tenant_id: $tenant_id, model_id: $model_id})
            SET m.version = $version, m.updated_at = datetime()
            """,
            tenant_id=tenant_id,
            model_id=model_id,
            version=version,
        )
        for node in nodes:
            await tx.run(
                """
                MERGE (n:GraphNode {tenant_id: $tenant_id, id: $id})
                SET n.kind = $kind, n.label = $label, n.properties = $properties
                WITH n
                MATCH (m:ContextModel {tenant_id: $tenant_id, model_id: $model_id})
                MERGE (m)-[:HAS_NODE]->(n)
                """,
                tenant_id=tenant_id,
                model_id=model_id,
                id=node["id"],
                kind=node["kind"],
                label=node["label"],
                properties=node.get("properties", {}),
            )
        for edge in edges:
            await tx.run(
                """
                MATCH (s:GraphNode {tenant_id: $tenant_id, id: $source})
                MATCH (t:GraphNode {tenant_id: $tenant_id, id: $target})
                MERGE (s)-[r:RELATES {relationship: $relationship}]->(t)
                SET r.properties = $properties
                """,
                tenant_id=tenant_id,
                source=edge["source"],
                target=edge["target"],
                relationship=edge["relationship"],
                properties=edge.get("properties", {}),
            )

    async def ping(self) -> bool:
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                return bool(record and record["ok"] == 1)
        except Exception:
            return False
