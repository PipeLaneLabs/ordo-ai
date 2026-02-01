"""Unit tests for OpenRouterClient - DeepSeek integration, token counting, cost calculation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import LLMProviderError
from src.llm.openrouter_client import OpenRouterClient


class TestOpenRouterClient:
    """Test suite for OpenRouterClient."""

    @pytest.fixture
    def client(self):
        """Create OpenRouterClient instance with mock API key."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test_api_key_1234567890"
            return OpenRouterClient(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_generate_success(self, client):
        """Test successful text generation."""
        mock_response_data = {
            "choices": [
                {
                    "message": {"content": "Generated response"},
                    "finish_reason": "stop",
                }
            ],
            "model": "deepseek/deepseek-chat",
            "usage": {"total_tokens": 150},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            # Create proper async mock for httpx response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(
                return_value=mock_response_data
            )  # Return the dict!
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            response = await client.generate(
                prompt="Test prompt",
                temperature=0.7,
                max_tokens=1000,
                model="deepseek/deepseek-chat",  # Explicitly specify model
            )

            assert response.content == "Generated response"
            assert response.model == "deepseek/deepseek-chat"
            assert response.tokens_used == 150
            assert response.cost_usd == 0.0  # DeepSeek is free

    @pytest.mark.asyncio
    async def test_generate_http_error(self, client):
        """Test HTTP error handling."""
        import httpx

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "500 Internal Server Error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            )
            mock_post.return_value = mock_response

            with pytest.raises(LLMProviderError) as exc_info:
                await client.generate(prompt="Test")

            # Error should mention retries since it goes through retry logic
            assert "failed after" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_rate_limit(self, client):
        """Test rate limit error handling."""
        import httpx

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "429 Rate Limit",
                    request=MagicMock(),
                    response=MagicMock(status_code=429),
                )
            )
            mock_post.return_value = mock_response

            with pytest.raises(LLMProviderError) as exc_info:
                await client.generate(prompt="Test")

            # Just verify it failed - details structure depends on retry logic
            assert "failed after" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_missing_content(self, client):
        """Test handling of malformed API response."""
        mock_response = {
            "choices": [{"message": {}}],  # Missing 'content'
            "model": "test-model",
            "usage": {"total_tokens": 0},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=mock_response)
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            with pytest.raises(LLMProviderError) as exc_info:
                await client.generate(prompt="Test")

            # Error should mention retries
            assert "failed after" in str(exc_info.value)

    def test_count_tokens_deepseek(self, client):
        """Test token counting for DeepSeek models using tiktoken."""
        text = "This is a test sentence for token counting"
        tokens = client.count_tokens(text, model="deepseek/deepseek-chat")

        # tiktoken cl100k_base encoding
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_fallback(self, client):
        """Test fallback token counting for non-DeepSeek models."""
        text = "This is a test sentence"
        tokens = client.count_tokens(text, model="google/gemini-flash-1.5")

        # Simple word count fallback
        assert tokens == 5

    def test_calculate_cost_free_model(self, client):
        """Test cost calculation for free DeepSeek model."""
        cost = client.calculate_cost(
            tokens_prompt=500, tokens_completion=500, model="deepseek/deepseek-chat"
        )
        assert cost == 0.0

    def test_calculate_cost_paid_model(self, client):
        """Test cost calculation for paid models."""
        # deepseek-v3.2: $0.27/1M input, $1.10/1M output
        cost = client.calculate_cost(
            tokens_prompt=500_000,
            tokens_completion=500_000,
            model="deepseek/deepseek-v3.2",  # Use model that's in MODEL_COSTS
        )
        # (500k/1M * 0.27) + (500k/1M * 1.10) = 0.135 + 0.55 = 0.685
        assert cost == pytest.approx(0.685, rel=0.01)

    def test_calculate_cost_unknown_model(self, client):
        """Test cost calculation fallback for unknown models."""
        cost = client.calculate_cost(
            tokens_prompt=500, tokens_completion=500, model="unknown/model"
        )
        # Unknown models return 0.0 (assumed free per implementation)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_model_selection(self, client):
        """Test model parameter is passed correctly."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(
                return_value={
                    "choices": [{"message": {"content": "response"}}],
                    "model": "deepseek/deepseek-r1",
                    "usage": {"total_tokens": 100},
                }
            )
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            await client.generate(
                prompt="Test",
                model="deepseek/deepseek-r1",
            )

            # Verify model was passed in request
            call_args = mock_post.call_args
            json_data = call_args.kwargs["json"]
            assert json_data["model"] == "deepseek/deepseek-r1"
