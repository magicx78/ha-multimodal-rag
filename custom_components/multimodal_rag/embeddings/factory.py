"""Factory and registry for embedding providers."""
from __future__ import annotations

import logging
from typing import Any, Type

from .base import EmbeddingProvider

_LOGGER = logging.getLogger(__name__)


class EmbeddingFactory:
    """Plugin-based factory for embedding providers.

    Usage:
        EmbeddingFactory.register("claude", ClaudeEmbeddingProvider)
        provider = EmbeddingFactory.create("claude", model="...", api_key="...")
    """

    _providers: dict[str, Type[EmbeddingProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[EmbeddingProvider]) -> None:
        """Register an embedding provider class.

        Args:
            name: Unique identifier (e.g. "claude", "sentence_transformers").
            provider_class: Class that subclasses EmbeddingProvider.
        """
        if not issubclass(provider_class, EmbeddingProvider):
            raise TypeError(
                f"{provider_class.__name__} must subclass EmbeddingProvider"
            )
        cls._providers[name] = provider_class
        _LOGGER.debug("Registered embedding provider: %s", name)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> EmbeddingProvider:
        """Instantiate a registered embedding provider.

        Args:
            name: Provider name as registered.
            **kwargs: Constructor arguments.

        Returns:
            Configured EmbeddingProvider instance.

        Raises:
            ValueError: If the provider name is unknown.
        """
        if name not in cls._providers:
            available = ", ".join(cls._providers.keys()) or "none"
            raise ValueError(
                f"Unknown embedding provider {name!r}. Available: {available}"
            )
        _LOGGER.debug("Creating embedding provider: %s", name)
        return cls._providers[name](**kwargs)

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return list of registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider name is registered."""
        return name in cls._providers
