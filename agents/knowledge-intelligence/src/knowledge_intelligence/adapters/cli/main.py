"""CLI: gie-knowledge"""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import typer
from rich import print as rprint

from gie_contracts.knowledge import KnowledgeQueryRequest

app = typer.Typer(name="gie-knowledge", help="GIE Knowledge Intelligence CLI")


@app.command()
def query(q: str, top_k: int = 5, domain: str | None = None, memory: bool = True):
    """Run explainable knowledge query."""
    asyncio.run(_query(q, top_k, domain, memory))


async def _query(q: str, top_k: int, domain: str | None, memory: bool):
    from knowledge_intelligence.infrastructure.bootstrap import build_container
    from knowledge_intelligence.seed.loader import seed_builtin_knowledge
    from gie_contracts.knowledge import KnowledgeDomain

    container = await build_container(memory=memory)
    await seed_builtin_knowledge(container)
    domains = [KnowledgeDomain(domain)] if domain else []
    result = await container.query_engine.query(
        KnowledgeQueryRequest(query=q, domains=domains, top_k=top_k),
        tenant_id="cli",
        correlation_id=uuid4().hex,
    )
    rprint(json.dumps(result.model_dump(mode="json"), indent=2))


@app.command("seed")
def seed_cmd(memory: bool = True):
    """Load built-in knowledge corpora."""
    asyncio.run(_seed(memory))


async def _seed(memory: bool):
    from knowledge_intelligence.infrastructure.bootstrap import build_container
    from knowledge_intelligence.seed.loader import seed_builtin_knowledge

    container = await build_container(memory=memory)
    n = await seed_builtin_knowledge(container)
    rprint(f"Seeded {n} nodes")


@app.command()
def version():
    from knowledge_intelligence.version import AGENT_NAME, AGENT_VERSION

    rprint(f"{AGENT_NAME} {AGENT_VERSION}")


if __name__ == "__main__":
    app()
