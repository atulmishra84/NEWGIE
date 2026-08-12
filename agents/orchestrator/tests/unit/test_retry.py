import pytest
from orchestrator.domain.retry import RetryableError, with_retry


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableError("unavailable")
        return "ok"

    result, retries = await with_retry(flaky, max_attempts=4, base_delay_ms=1)
    assert result == "ok"
    assert retries == 2
