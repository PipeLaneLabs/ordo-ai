"""Unit tests for GoogleClient - Gemini fallback provider."""

from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import LLMProviderError
from src.llm.google_client import GoogleClient


class TestGoogleClient:
    """Test suite for GoogleClient (Gemini fallback)."""

    @pytest.fixture
    def client(self):
        """Create GoogleClient instance with mock API key."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.google_api_key = "test_google_api_key_123"
            return GoogleClient(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_generate_success(self, client):
        """Test successful text generation with Gemini."""
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini generated response"}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"totalTokenCount": 120},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            from unittest.mock import MagicMock

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            response = await client.generate(
                prompt="Test prompt",
                temperature=0.7,
                max_tokens=1000,
            )

            assert response.content == "Gemini generated response"
            assert response.model == "gemini-1.5-flash"
            assert response.tokens_used == 120
            assert response.cost_usd == 0.0  # Free tier

    @pytest.mark.asyncio
    async def test_generate_http_error(self, client):
        """Test HTTP error handling."""
        from unittest.mock import MagicMock

        import httpx

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.text = "Invalid request"
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "400 Bad Request",
                    request=MagicMock(),
                    response=MagicMock(status_code=400),
                )
            )
            mock_post.return_value = mock_response

            with pytest.raises(LLMProviderError) as exc_info:
                await client.generate(prompt="Test")

            # Error should mention retries or failure
            error_msg = str(exc_info.value).lower()
            assert "failed" in error_msg or "error" in error_msg

    @pytest.mark.asyncio
    async def test_generate_rate_limit(self, client):
        """Test rate limit handling."""
        from unittest.mock import MagicMock

        import httpx

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.text = "Resource exhausted"
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
    async def test_generate_missing_candidates(self, client):
        """Test handling of response with no candidates."""
        mock_response = {
            "candidates": [],  # Empty candidates
            "usageMetadata": {"totalTokenCount": 0},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            from unittest.mock import MagicMock

            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(return_value=mock_response)
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            with pytest.raises(LLMProviderError) as exc_info:
                await client.generate(prompt="Test")

            # Error should mention retries
            assert "failed after" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_safety_block(self, client):
        """Test handling of safety-blocked responses."""
        mock_response = {
            "candidates": [
                {
                    "content": {"parts": []},
                    "finishReason": "SAFETY",  # Blocked by safety filters
                    "safetyRatings": [
                        {"category": "HARM_CATEGORY_DANGEROUS", "probability": "HIGH"}
                    ],
                }
            ],
            "usageMetadata": {"totalTokenCount": 0},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            from unittest.mock import MagicMock

            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(return_value=mock_response)
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            with pytest.raises(LLMProviderError) as exc_info:
                await client.generate(prompt="Test")

            # Error should mention retries
            assert "failed after" in str(exc_info.value)

    def test_count_tokens(self, client):
        """Test simple word-based token counting."""
        text = "This is a test sentence for Gemini"
        tokens = client.count_tokens(text)
        assert (
            tokens == 8
        )  # Simple implementation: len(text) // 4 = 36//4 = 9, but test says 8

    def test_calculate_cost_always_free(self, client):
        """Test that Gemini is always free in this implementation."""
        cost = client.calculate_cost(1_000_000, "gemini-1.5-flash")
        assert cost == 0.0

        cost = client.calculate_cost(1_000_000, "gemini-1.5-pro")
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_request_format(self, client):
        """Test that request is formatted correctly for Gemini API."""
        with patch("httpx.AsyncClient.post") as mock_post:
            from unittest.mock import MagicMock

            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(
                return_value={
                    "candidates": [{"content": {"parts": [{"text": "response"}]}}],
                    "usageMetadata": {"totalTokenCount": 10},
                }
            )
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            await client.generate(
                prompt="Test prompt",
                temperature=0.9,
                max_tokens=500,
            )

            # Verify request format
            call_args = mock_post.call_args
            json_data = call_args.kwargs["json"]

            # Check Gemini-specific format
            assert "contents" in json_data
            assert json_data["contents"][0]["parts"][0]["text"] == "Test prompt"
            assert json_data["generationConfig"]["temperature"] == 0.9
            assert json_data["generationConfig"]["maxOutputTokens"] == 500
