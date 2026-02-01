"""Base LLM client interface with retry logic and timeout handling.

This module provides an abstract base class for all LLM provider implementations.
Implements retry logic with exponential backoff and standardized error handling.
"""

import asyncio
from abc import ABC, abstractmethod

import structlog
from pydantic import BaseModel, Field

from src.exceptions import (
    BudgetExhaustedError,
    LLMProviderError,
)


class LLMResponse(BaseModel):
    """Standardized response from LLM providers."""

    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model used for generation")
    tokens_used: int = Field(..., description="Total tokens consumed")
    tokens_prompt: int = Field(0, description="Tokens in prompt")
    tokens_completion: int = Field(0, description="Tokens in completion")
    cost_usd: float = Field(0.0, description="Cost in USD")
    latency_ms: int = Field(..., description="Response time in milliseconds")
    provider: str = Field(..., description="Provider name (openrouter/google)")
    finish_reason: str | None = Field(
        None, description="Reason for completion (stop/length/error)"
    )


class BaseLLMClient(ABC):
    """Abstract base class for LLM provider clients.

    All LLM providers (OpenRouter, Google) must implement this interface.
    Provides retry logic, timeout handling, and standardized error handling.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        timeout_seconds: Request timeout in seconds (default: 300 = 5 minutes)
        retry_delay: Initial retry delay in seconds (default: 1)
        backoff_factor: Exponential backoff multiplier (default: 2)
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> None:
        """Initialize base LLM client.

        Args:
            max_retries: Maximum retry attempts for failed requests
            timeout_seconds: Request timeout (5 minutes default per ARCHITECTURE.md)
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop: list[str] | None = None,
        **_kwargs: object,
    ) -> LLMResponse:
        """Generate text from a prompt.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            stop: Stop sequences to end generation
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMProviderError: On provider API failures
            BudgetExhaustedError: If token/cost limits exceeded
        """

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        max_tokens: int = 4000,
        temperature: float = 0.4,
        **_kwargs: object,
    ) -> BaseModel:
        """Generate structured output conforming to a Pydantic schema.

        Args:
            prompt: Input text prompt
            schema: Pydantic model class for structured output
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower for structured outputs)
            **kwargs: Provider-specific parameters

        Returns:
            Instance of schema class with parsed LLM response

        Raises:
            LLMProviderError: On provider API failures or parsing errors
            BudgetExhaustedError: If token/cost limits exceeded
        """
        # Default implementation: generate text and parse
        # Providers can override for native structured output support
        import json

        structured_prompt = (
            f"{prompt}\n\n"
            f"Respond with valid JSON matching this schema:\n"
            f"{schema.model_json_schema()}\n\n"
            f"JSON response:"
        )

        response = await self.generate(
            prompt=structured_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            # Extract JSON from response (handles markdown code blocks)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            raise LLMProviderError(
                message=f"Failed to parse structured output: {e}",
                provider=response.provider,
                details={
                    "schema": schema.__name__,
                    "response_content": response.content[:500],
                },
            ) from e

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using provider-specific tokenizer.

        Args:
            text: Input text to tokenize

        Returns:
            Number of tokens
        """

    @abstractmethod
    def calculate_cost(self, tokens_prompt: int, tokens_completion: int) -> float:
        """Calculate cost in USD for token usage.

        Args:
            tokens_prompt: Input prompt tokens
            tokens_completion: Generated completion tokens

        Returns:
            Cost in USD (0.0 for free models)
        """

    async def _retry_with_backoff(
        self,
        operation: object,
        operation_name: str,
    ) -> object:
        """Execute operation with exponential backoff retry logic.

        Args:
            operation: Async callable to execute
            operation_name: Description for error messages

        Returns:
            Operation result on success

        Raises:
            LLMProviderError: After max retries exceeded
        """
        log = structlog.get_logger()
        last_error: Exception | None = None
        delay = self.retry_delay

        for attempt in range(self.max_retries):
            try:
                # Execute with timeout
                return await asyncio.wait_for(
                    operation(),
                    timeout=self.timeout_seconds,
                )
            except TimeoutError as e:
                last_error = e
                log.warning(
                    "llm_operation_timeout",
                    timeout_seconds=self.timeout_seconds,
                    attempt=attempt + 1,
                )
            except LLMProviderError as e:
                last_error = e
                # Don't retry on budget errors
                if isinstance(e, BudgetExhaustedError):
                    raise
                # Retry on rate limits (429) or server errors (500+)
                if e.details and isinstance(e.details.get("status_code"), int):
                    status = e.details["status_code"]
                    if status == 429:
                        log.warning(
                            "rate_limit_hit",
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                        )
                    elif status >= 500:
                        log.warning(
                            "server_error",
                            status=status,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                        )
                    else:
                        # Client error (4xx), don't retry
                        raise
                else:
                    log.warning(
                        "llm_operation_failed", error=str(e), attempt=attempt + 1
                    )
            except Exception as e:
                last_error = e
                log.warning("llm_operation_error", error=str(e), attempt=attempt + 1)

            # Retry with backoff if not last attempt
            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= self.backoff_factor
                # Cap delay at 60 seconds per TASKS.md
                delay = min(delay, 60.0)

        # All retries exhausted
        raise LLMProviderError(
            message=f"{operation_name} failed after {self.max_retries} retries",
            provider=self.__class__.__name__,
            details={
                "last_error": str(last_error),
                "attempts": self.max_retries,
            },
        ) from last_error

    def _get_provider_name(self) -> str:
        """Get provider name from class name.

        Returns:
            Provider name (e.g., 'openrouter', 'google')
        """
        class_name = self.__class__.__name__.lower()
        if "openrouter" in class_name:
            return "openrouter"
        elif "google" in class_name:
            return "google"
        else:
            return "unknown"
