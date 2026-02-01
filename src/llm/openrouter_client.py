"""OpenRouter API client for DeepSeek and Gemini models.

Primary LLM provider with support for:
- deepseek/deepseek-v3.2 (PAID, strongest coder)
- deepseek/deepseek-r1-0528:free (FREE, reasoning)
- google/gemini-2.5-flash (FREE, fast)
"""

import time
from typing import ClassVar, cast

import httpx

from src.config import Settings
from src.exceptions import LLMProviderError
from src.llm.base_client import BaseLLMClient, LLMResponse


class OpenRouterClient(BaseLLMClient):
    """OpenRouter API client with automatic retry and cost tracking.

    Attributes:
        api_key: OpenRouter API key from settings
        base_url: OpenRouter API endpoint
        default_model: Default model to use if not specified
        model_costs: Pricing per 1M tokens (prompt/completion)
    """

    # Model pricing per 1M tokens (as of 2026-01-21)
    MODEL_COSTS: ClassVar[dict[str, dict[str, float]]] = {
        "deepseek/deepseek-v3.2": {
            "prompt": 0.27,  # $0.27 per 1M input tokens
            "completion": 1.10,  # $1.10 per 1M output tokens
        },
        "deepseek/deepseek-r1-0528:free": {
            "prompt": 0.0,
            "completion": 0.0,
        },
        "google/gemini-2.5-flash": {
            "prompt": 0.0,
            "completion": 0.0,
        },
    }

    def __init__(
        self,
        settings: Settings,
        default_model: str = "google/gemini-2.5-flash",
        **_kwargs: object,
    ) -> None:
        """Initialize OpenRouter client.

        Args:
            settings: Application settings with OPENROUTER_API_KEY
            default_model: Default model to use
            **_kwargs: Additional arguments passed to BaseLLMClient
        """
        super().__init__()
        self.api_key = settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
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
        """Generate text using OpenRouter API.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            stop: Stop sequences
            model: Model name (uses default_model if None)
            **kwargs: Additional OpenRouter parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMProviderError: On API failures or rate limits
        """
        model = model or self.default_model
        start_time = time.time()

        async def _call_api() -> LLMResponse:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                if stop:
                    payload["stop"] = stop

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=self.timeout_seconds,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Extract response data
                    choice = data["choices"][0]
                    usage = data.get("usage", {})

                    tokens_prompt = usage.get("prompt_tokens", 0)
                    tokens_completion = usage.get("completion_tokens", 0)
                    tokens_total = usage.get(
                        "total_tokens", tokens_prompt + tokens_completion
                    )

                    # Calculate cost
                    cost_usd = self.calculate_cost(
                        tokens_prompt, tokens_completion, model
                    )

                    latency_ms = int((time.time() - start_time) * 1000)

                    return LLMResponse(
                        content=choice["message"]["content"],
                        model=model,
                        tokens_used=tokens_total,
                        tokens_prompt=tokens_prompt,
                        tokens_completion=tokens_completion,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                        provider="openrouter",
                        finish_reason=choice.get("finish_reason"),
                    )

                except httpx.HTTPStatusError as e:
                    raise LLMProviderError(
                        message=f"OpenRouter API error: {e.response.text}",
                        provider="openrouter",
                        details={
                            "status_code": e.response.status_code,
                            "model": model,
                            "response": e.response.text[:500],
                        },
                    ) from e
                except httpx.RequestError as e:
                    raise LLMProviderError(
                        message=f"OpenRouter request failed: {e!s}",
                        provider="openrouter",
                        details={"model": model, "error": str(e)},
                    ) from e

        return cast(
            LLMResponse,
            await self._retry_with_backoff(
                _call_api,
                f"OpenRouter generate ({model})",
            ),
        )

    def count_tokens(self, text: str, model: str | None = None) -> int:
        """Count tokens using model-specific tokenizer.

        Args:
            text: Input text to tokenize
            model: Model name (for model-specific counting)

        Returns:
            Estimated token count
        """
        model = model or self.default_model

        # DeepSeek models use tiktoken (similar to GPT-4)
        if "deepseek" in model.lower():
            try:
                import tiktoken

                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(text))
            except ImportError:
                # Fallback: rough estimate (4 chars per token)
                return len(text) // 4

        # Gemini models use Google tokenizer (approximate)
        elif "gemini" in model.lower():
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4

        else:
            # Default fallback
            return len(text) // 4

    def calculate_cost(
        self, tokens_prompt: int, tokens_completion: int, model: str | None = None
    ) -> float:
        """Calculate cost in USD for token usage.

        Args:
            tokens_prompt: Input prompt tokens
            tokens_completion: Generated completion tokens
            model: Model name (uses default_model if None)

        Returns:
            Cost in USD (0.0 for free models)
        """
        model = model or self.default_model

        if model not in self.MODEL_COSTS:
            # Unknown model, assume free
            return 0.0

        pricing = self.MODEL_COSTS[model]
        cost_prompt = (tokens_prompt / 1_000_000) * pricing["prompt"]
        cost_completion = (tokens_completion / 1_000_000) * pricing["completion"]

        return round(cost_prompt + cost_completion, 6)
