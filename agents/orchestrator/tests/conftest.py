import pytest
import pytest_asyncio
from gie_contracts.orchestrator import AnalyzeRequest, ExecutionMode
from orchestrator.infrastructure.bootstrap import build_container
from orchestrator.settings import Settings

@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False, simulate_agents=True, retry_base_delay_ms=1, default_retries=2)

@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)

@pytest.fixture
def sample_analyze():
    return AnalyzeRequest(
        tenant_id="acme",
        source={"type": "folder", "path": "/tmp/demo-ai-app"},
        mode=ExecutionMode.SYNC,
        cache=True,
        options={"parallel": True},
    )
