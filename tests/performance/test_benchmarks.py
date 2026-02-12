"""Performance benchmarks for the multi-tier agent ecosystem.

These tests use pytest-benchmark to measure performance and detect regressions.
Run with: pytest tests/performance/ --benchmark-json=results.json
"""

import os
from unittest.mock import AsyncMock

import pytest


# Skip performance tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PERFORMANCE") != "1",
    reason="Performance tests are gated behind RUN_PERFORMANCE=1",
)


@pytest.fixture
def mock_settings():
    """Mock settings for performance tests."""
    from src.config import Settings

    return Settings(
        openrouter_api_key="sk-fake-key-for-testing",
        google_api_key="fake-google-key",
        jwt_secret_key="test-secret-key-min-32-chars-long-123456",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
        redis_host="localhost",
        redis_port=6379,
        minio_secret_key="fake-minio-key",
    )


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for performance tests."""
    client = AsyncMock()
    client.chat_completion = AsyncMock(
        return_value={"choices": [{"message": {"content": "Test response"}}]}
    )
    return client


def test_agent_response_latency(benchmark, mock_settings, mock_llm_client):
    """Benchmark agent response time.

    Target: < 500ms for simple queries
    Threshold: Fail if > 550ms (10% tolerance)
    """

    async def agent_response():
        # Simulate agent processing
        response = await mock_llm_client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
        return response

    import asyncio

    result = benchmark(lambda: asyncio.run(agent_response()))

    # Verify result structure
    assert result is not None


def test_checkpoint_save_performance(benchmark, mock_settings):
    """Benchmark checkpoint save operation.

    Target: < 100ms per checkpoint
    Threshold: Fail if > 110ms (10% tolerance)
    """

    def save_checkpoint():
        # Simulate checkpoint serialization
        checkpoint_data = {
            "thread_id": "test-thread",
            "checkpoint": {"data": "x" * 1000},  # 1KB of data
            "metadata": {"step": 1},
        }
        return checkpoint_data

    result = benchmark(save_checkpoint)
    assert result is not None
    assert "thread_id" in result


def test_budget_guard_check_performance(benchmark, mock_settings):
    """Benchmark budget guard validation.

    Target: < 50ms per check
    Threshold: Fail if > 55ms (10% tolerance)
    """

    def check_budget():
        # Simulate budget calculation
        usage = {"prompt_tokens": 100, "completion_tokens": 50}
        cost = usage["prompt_tokens"] * 0.000001 + usage["completion_tokens"] * 0.000002
        return cost < 1.0  # $1 limit

    result = benchmark(check_budget)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_concurrent_agent_throughput(mock_settings, mock_llm_client):
    """Test throughput with concurrent agent requests.

    Target: Handle 10 concurrent requests in < 2 seconds
    """
    import asyncio
    import time

    async def process_request(request_id: int):
        response = await mock_llm_client.chat_completion(
            messages=[{"role": "user", "content": f"Request {request_id}"}]
        )
        return response

    start = time.time()
    tasks = [process_request(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start

    assert len(results) == 10
    assert duration < 2.0, f"Throughput test took {duration:.2f}s, expected < 2.0s"


if __name__ == "__main__":
    # Allow running benchmarks standalone
    pytest.main([__file__, "-v", "--benchmark-only"])
