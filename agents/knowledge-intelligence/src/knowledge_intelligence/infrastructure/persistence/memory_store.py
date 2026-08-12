"""In-memory repositories for local/dev/tests; mirrors Postgres contracts."""

from __future__ import annotations

import copy
from typing import Any

from gie_contracts.knowledge import (
    KnowledgeDiff,
    KnowledgeEdge,
    KnowledgeGraphSnapshot,
    KnowledgeNode,
)

from knowledge_intelligence.domain.ports import (
    KnowledgeEdgeRepository,
    KnowledgeNodeRepository,
    VersionRepository,
)


class InMemoryNodeRepository(KnowledgeNodeRepository):
    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._versions: dict[str, dict[str, KnowledgeNode]] = {}

    async def upsert_nodes(self, nodes: list[KnowledgeNode]) -> int:
        for n in nodes:
            self._nodes[n.node_id] = n
            bucket = self._versions.setdefault(n.version, {})
            bucket[n.node_id] = n
        return len(nodes)

    async def get_node(
        self, node_id: str, version: str | None = None
    ) -> KnowledgeNode | None:
        if version and version in self._versions:
            return self._versions[version].get(node_id)
        return self._nodes.get(node_id)

    async def list_nodes(
        self,
        *,
        domain: str | None = None,
        kind: str | None = None,
        version: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeNode]:
        source = (
            list(self._versions[version].values())
            if version and version in self._versions
            else list(self._nodes.values())
        )
        out = []
        for n in source:
            if domain and n.domain.value != domain:
                continue
            if kind and n.kind.value != kind:
                continue
            if not n.active:
                continue
            out.append(n)
        return out[offset : offset + limit]

    async def soft_delete(self, node_id: str) -> bool:
        n = self._nodes.get(node_id)
        if not n:
            return False
        n.active = False
        return True


class InMemoryEdgeRepository(KnowledgeEdgeRepository):
    def __init__(self) -> None:
        self._edges: dict[str, KnowledgeEdge] = {}

    async def upsert_edges(self, edges: list[KnowledgeEdge]) -> int:
        for e in edges:
            self._edges[e.edge_id] = e
        return len(edges)

    async def neighbors(self, node_id: str, depth: int = 1) -> list[KnowledgeEdge]:
        # depth=1 only in memory impl
        return [
            e
            for e in self._edges.values()
            if e.source_id == node_id or e.target_id == node_id
        ]


class InMemoryVersionRepository(VersionRepository):
    def __init__(
        self, nodes: InMemoryNodeRepository, edges: InMemoryEdgeRepository
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._snapshots: dict[str, KnowledgeGraphSnapshot] = {}
        self._node_sets: dict[str, set[str]] = {}
        self._edge_sets: dict[str, set[str]] = {}

    async def publish(
        self, version: str, checksum: str, node_count: int, edge_count: int
    ) -> KnowledgeGraphSnapshot:
        snap = KnowledgeGraphSnapshot(
            version=version,
            node_count=node_count,
            edge_count=edge_count,
            domains=list({n.domain for n in self._nodes._nodes.values()}),
            checksum=checksum,
        )
        self._snapshots[version] = snap
        self._node_sets[version] = set(self._nodes._nodes.keys())
        self._edge_sets[version] = set(self._edges._edges.keys())
        return snap

    async def latest(self) -> KnowledgeGraphSnapshot | None:
        if not self._snapshots:
            return None
        return self._snapshots[sorted(self._snapshots.keys())[-1]]

    async def get(self, version: str) -> KnowledgeGraphSnapshot | None:
        return self._snapshots.get(version)

    async def diff(self, from_version: str, to_version: str) -> KnowledgeDiff:
        a = self._node_sets.get(from_version, set())
        b = self._node_sets.get(to_version, set())
        ea = self._edge_sets.get(from_version, set())
        eb = self._edge_sets.get(to_version, set())
        return KnowledgeDiff(
            from_version=from_version,
            to_version=to_version,
            added_nodes=sorted(b - a),
            removed_nodes=sorted(a - b),
            changed_nodes=[],
            added_edges=sorted(eb - ea),
            removed_edges=sorted(ea - eb),
        )


class InMemoryGraphRepository:
    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []

    async def project_nodes(self, nodes: list[KnowledgeNode]) -> None:
        for n in nodes:
            self._nodes[n.node_id] = {
                "id": n.node_id,
                "kind": n.kind.value,
                "title": n.title,
                "domain": n.domain.value,
            }

    async def project_edges(self, edges: list[KnowledgeEdge]) -> None:
        for e in edges:
            self._edges.append(
                {
                    "id": e.edge_id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "relationship": e.relationship.value,
                }
            )

    async def shortest_paths(
        self, source_id: str, target_id: str, max_depth: int = 4
    ) -> list[list[str]]:
        # BFS
        from collections import deque

        adj: dict[str, list[str]] = {}
        for e in self._edges:
            adj.setdefault(e["source"], []).append(e["target"])
            adj.setdefault(e["target"], []).append(e["source"])
        q = deque([(source_id, [source_id])])
        seen = {source_id}
        paths: list[list[str]] = []
        while q:
            node, path = q.popleft()
            if len(path) > max_depth + 1:
                continue
            if node == target_id and len(path) > 1:
                paths.append(path)
                continue
            for nxt in adj.get(node, []):
                if nxt not in seen or nxt == target_id:
                    seen.add(nxt)
                    q.append((nxt, path + [nxt]))
        return paths[:5]

    async def expand(
        self, node_ids: list[str], hops: int = 1
    ) -> tuple[list[str], list[dict[str, Any]]]:
        frontier = set(node_ids)
        for _ in range(hops):
            nxt: set[str] = set()
            for e in self._edges:
                if e["source"] in frontier:
                    nxt.add(e["target"])
                if e["target"] in frontier:
                    nxt.add(e["source"])
            frontier |= nxt
        expanded = sorted(frontier - set(node_ids))
        return expanded, [self._nodes[i] for i in expanded if i in self._nodes]

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._items: dict[str, tuple[list[float], dict[str, Any]]] = {}

    async def upsert(
        self, ids: list[str], vectors: list[list[float]], payloads: list[dict[str, Any]]
    ) -> None:
        for i, v, p in zip(ids, vectors, payloads):
            self._items[i] = (v, p)

    async def search(
        self, vector: list[float], top_k: int, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        def cos(a: list[float], b: list[float]) -> float:
            return sum(x * y for x, y in zip(a, b))

        results = []
        for i, (v, p) in self._items.items():
            if filters:
                if "domain" in filters and p.get("domain") not in filters["domain"]:
                    continue
                if "kind" in filters and p.get("kind") not in filters["kind"]:
                    continue
                if "version" in filters and p.get("version") != filters["version"]:
                    continue
            results.append({"id": i, "score": cos(vector, v), "payload": p})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def ping(self) -> bool:
        return True


class InMemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    async def get_json(self, key: str) -> dict[str, Any] | None:
        return copy.deepcopy(self._data.get(key))

    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None:
        self._data[key] = copy.deepcopy(value)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)


class LoggingEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(
        self, topic: str, event: dict[str, Any], key: str | None = None
    ) -> None:
        self.events.append({"topic": topic, "key": key, "event": event})
