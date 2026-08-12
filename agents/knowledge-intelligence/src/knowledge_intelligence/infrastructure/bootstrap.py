"""Wire production or in-memory container."""

from __future__ import annotations

from knowledge_intelligence.application.di import Container, set_container
from knowledge_intelligence.infrastructure.cache.redis_cache import (
    RedisCacheStore,
    create_redis_client,
)
from knowledge_intelligence.infrastructure.embeddings.hash_embedder import (
    HashEmbeddingService,
)
from knowledge_intelligence.infrastructure.messaging.kafka_publisher import (
    KafkaEventPublisher,
)
from knowledge_intelligence.infrastructure.persistence.memory_store import (
    InMemoryCache,
    InMemoryEdgeRepository,
    InMemoryGraphRepository,
    InMemoryNodeRepository,
    InMemoryVectorStore,
    InMemoryVersionRepository,
    LoggingEventPublisher,
)
from knowledge_intelligence.infrastructure.persistence.neo4j_repo import (
    Neo4jKnowledgeGraph,
)
from knowledge_intelligence.infrastructure.persistence.postgres import (
    PostgresEdgeRepository,
    PostgresNodeRepository,
    PostgresVersionRepository,
    init_db,
)
from knowledge_intelligence.infrastructure.vector.qdrant_store import (
    QdrantKnowledgeStore,
)
from knowledge_intelligence.settings import Settings, get_settings


async def build_container(
    *, memory: bool = False, settings: Settings | None = None
) -> Container:
    settings = settings or get_settings()
    embeddings = HashEmbeddingService(dim=settings.embedding_dim)
    if memory or settings.gie_env == "test":
        nodes = InMemoryNodeRepository()
        edges = InMemoryEdgeRepository()
        container = Container(
            settings=settings,
            nodes=nodes,
            edges=edges,
            graph=InMemoryGraphRepository(),
            vectors=InMemoryVectorStore(),
            embeddings=embeddings,
            versions=InMemoryVersionRepository(nodes, edges),
            cache=InMemoryCache(),
            events=LoggingEventPublisher(),
        )
        set_container(container)
        return container

    await init_db(settings)
    redis = create_redis_client(settings)
    container = Container(
        settings=settings,
        nodes=PostgresNodeRepository(),
        edges=PostgresEdgeRepository(),
        graph=Neo4jKnowledgeGraph.from_settings(settings),
        vectors=QdrantKnowledgeStore.from_settings(settings),
        embeddings=embeddings,
        versions=PostgresVersionRepository(),
        cache=RedisCacheStore(redis),
        events=KafkaEventPublisher(settings.kafka_bootstrap_servers),
    )
    set_container(container)
    return container
