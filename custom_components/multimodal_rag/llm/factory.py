"""Factory and registry for LLM providers."""
from __future__ import annotations

import logging
from typing import Any, Type

from .base import LLMProvider

_LOGGER = logging.getLogger(__name__)


class LLMFactory:
    """Plugin-based factory for creating LLM provider instances.

    Providers register themselves by name. The factory resolves
    the correct class at runtime, making it trivial to add new
    backends without touching the RAG engine.

    Usage:
        LLMFactory.register("claude", ClaudeProvider)
        provider = LLMFactory.create("claude", model="...", api_key="...")
    """

    _providers: dict[str, Type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """Register an LLM provider class under a given name.

        Args:
            name: Unique identifier (e.g. "claude", "ollama").
            provider_class: Class that subclasses LLMProvider.
        """
        if not issubclass(provider_class, LLMProvider):
            raise TypeError(
                f"{provider_class.__name__} must subclass LLMProvider"
            )
        cls._providers[name] = provider_class
        _LOGGER.debug("Registered LLM provider: %s", name)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> LLMProvider:
        """Instantiate a registered LLM provider.

        Args:
            name: Provider name as registered.
            **kwargs: Constructor arguments forwarded to the provider.

        Returns:
            Configured LLMProvider instance.

        Raises:
            ValueError: If the provider name is not registered.
        """
        if name not in cls._providers:
            available = ", ".join(cls._providers.keys()) or "none"
            raise ValueError(
                f"Unknown LLM provider {name!r}. Available: {available}"
            )
        provider_class = cls._providers[name]
        _LOGGER.debug("Creating LLM provider: %s with kwargs keys: %s", name, list(kwargs.keys()))
        return provider_class(**kwargs)

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return list of registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider name is registered."""
        return name in cls._providers
