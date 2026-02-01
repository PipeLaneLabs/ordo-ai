"""Google Gemini API client as fallback provider.

Fallback client when OpenRouter fails or is unavailable.
Uses Google's direct API for gemini-1.5-flash model.
"""

import time
from typing import Any, cast

import httpx

from src.config import Settings
from src.exceptions import LLMProviderError
from src.llm.base_client import BaseLLMClient, LLMResponse


class GoogleClient(BaseLLMClient):
    """Google Gemini direct API client (fallback provider).

    Attributes:
        api_key: Google AI Studio API key
        base_url: Google Generative Language API endpoint
        default_model: Default Gemini model
    """

    def __init__(
        self,
        settings: Settings,
        default_model: str = "gemini-1.5-flash",
        **_kwargs: object,
    ) -> None:
        """Initialize Google Gemini client.

        Args:
            settings: Application settings with GOOGLE_API_KEY
            default_model: Default Gemini model
            **_kwargs: Additional arguments passed to BaseLLMClient
        """
        super().__init__()
        self.api_key = settings.google_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.default_model = default_model

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop: list[str] | None = None,
        model: str | None = None,
        **_kwargs: object,
    ) -> LLMResponse:
        """Generate text using Google Gemini API.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            stop: Stop sequences
            model: Model name (uses default_model if None)
            **kwargs: Additional Gemini parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMProviderError: On API failures
        """
        model = model or self.default_model
        start_time = time.time()

        async def _call_api() -> LLMResponse:
            async with httpx.AsyncClient() as client:
                # Google Gemini API endpoint format
                endpoint = (
                    f"{self.base_url}/models/{model}:generateContent"
                    f"?key={self.api_key}"
                )

                payload: dict[str, Any] = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": temperature,
                    },
                }

                if stop:
                    payload["generationConfig"]["stopSequences"] = stop

                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        timeout=self.timeout_seconds,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Extract response data
                    candidate = data["candidates"][0]
                    content = candidate["content"]["parts"][0]["text"]

                    # Token usage (Google provides this in usageMetadata)
                    usage = data.get("usageMetadata", {})
                    tokens_prompt = usage.get("promptTokenCount", 0)
                    tokens_completion = usage.get("candidatesTokenCount", 0)
                    tokens_total = usage.get(
                        "totalTokenCount", tokens_prompt + tokens_completion
                    )

                    # Cost is always 0.0 (free tier)
                    cost_usd = 0.0

                    latency_ms = int((time.time() - start_time) * 1000)

                    return LLMResponse(
                        content=content,
                        model=model,
                        tokens_used=tokens_total,
                        tokens_prompt=tokens_prompt,
                        tokens_completion=tokens_completion,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                        provider="google",
                        finish_reason=candidate.get("finishReason"),
                    )

                except httpx.HTTPStatusError as e:
                    raise LLMProviderError(
                        message=f"Google Gemini API error: {e.response.text}",
                        provider="google",
                        details={
                            "status_code": e.response.status_code,
                            "model": model,
                            "response": e.response.text[:500],
                        },
                    ) from e
                except httpx.RequestError as e:
                    raise LLMProviderError(
                        message=f"Google Gemini request failed: {e!s}",
                        provider="google",
                        details={"model": model, "error": str(e)},
                    ) from e
                except KeyError as e:
                    raise LLMProviderError(
                        message=f"Unexpected Google Gemini response format: {e}",
                        provider="google",
                        details={"model": model, "response": data},
                    ) from e

        return cast(
            LLMResponse,
            await self._retry_with_backoff(
                _call_api,
                f"Google Gemini generate ({model})",
            ),
        )

    def count_tokens(self, text: str) -> int:
        """Count tokens using rough estimation.

        Google tokenizer not available in free tier, so we use approximation.

        Args:
            text: Input text to tokenize

        Returns:
            Estimated token count (4 chars per token)
        """
        # Rough estimate: 4 characters per token
        return len(text) // 4

    def calculate_cost(
        self, _tokens_prompt: int, _tokens_completion: int
    ) -> float:
        """Calculate cost in USD for token usage.

        Args:
            tokens_prompt: Input prompt tokens
            tokens_completion: Generated completion tokens

        Returns:
            Always 0.0 (free tier)
        """
        return 0.0
