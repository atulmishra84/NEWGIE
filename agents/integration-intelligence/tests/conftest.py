import pytest
import pytest_asyncio
from gie_contracts.integration import AuthMethod, ConnectRequest, PlatformId
from integration_intelligence.infrastructure.bootstrap import build_container
from integration_intelligence.settings import Settings


@pytest.fixture
def settings():
    return Settings(
        gie_env="test",
        require_auth=False,
        circuit_failure_threshold=3,
        retry_max_attempts=2,
        retry_base_delay_ms=1,
    )


@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)


@pytest.fixture
def sample_connect():
    return ConnectRequest(
        tenant_id="acme",
        platform_id=PlatformId.GITHUB,
        name="acme-github",
        auth_method=AuthMethod.API_KEY,
        credentials={"api_key": "ghp_test"},
        config={"owner": "acme-org"},
        scopes=["repo", "workflow"],
    )
