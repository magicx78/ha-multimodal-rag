"""Base class and data models for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Return total token usage."""
        return self.usage.get("total_tokens", 0)


class LLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Every provider must implement generate() and reason().
    Providers are registered via LLMFactory and can be swapped
    without changing the RAG engine logic.
    """

    def __init__(self, model: str, **kwargs: Any) -> None:
        """Initialize the provider with a model name and optional config."""
        self.model = model
        self._config = kwargs

    @abstractmethod
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        """Generate a completion from a prompt with optional context.

        Args:
            prompt: The user prompt or instruction.
            context: Retrieved RAG context to include.

        Returns:
            LLMResponse with the generated text and metadata.
        """

    @abstractmethod
    async def reason(self, query: str, context: str) -> LLMResponse:
        """Answer a question by reasoning over retrieved context.

        Args:
            query: The user question.
            context: Concatenated retrieved document chunks.

        Returns:
            LLMResponse with the answer and source attribution.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the provider is reachable and the model is available.

        Returns:
            True if the provider is healthy, False otherwise.
        """

    @property
    def provider_name(self) -> str:
        """Return the canonical provider name used in config."""
        return self.__class__.__name__.lower().replace("provider", "")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
