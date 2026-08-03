import os
from pathlib import Path

import pytest
import pytest_asyncio

from knowledge_intelligence.infrastructure.bootstrap import build_container
from knowledge_intelligence.seed.loader import seed_builtin_knowledge
from knowledge_intelligence.settings import Settings

SEED = Path(__file__).resolve().parents[1] / "data" / "seed"


@pytest.fixture(autouse=True)
def _seed_env(monkeypatch):
    monkeypatch.setenv("GIE_KNOWLEDGE_SEED_PATH", str(SEED))
    monkeypatch.setenv("GIE_ENV", "test")


@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False, flag_enable_reindex_on_start=False)


@pytest_asyncio.fixture
async def container(settings):
    c = await build_container(memory=True, settings=settings)
    await seed_builtin_knowledge(c)
    return c
