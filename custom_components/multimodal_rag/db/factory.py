"""Factory and registry for vector database providers."""
from __future__ import annotations

import logging
from typing import Any, Type

from .base import VectorDBProvider

_LOGGER = logging.getLogger(__name__)


class VectorDBFactory:
    """Plugin-based factory for vector database providers.

    Usage:
        VectorDBFactory.register("qdrant", QdrantProvider)
        db = VectorDBFactory.create("qdrant", host="localhost", port=6333)
    """

    _providers: dict[str, Type[VectorDBProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[VectorDBProvider]) -> None:
        """Register a vector DB provider class.

        Args:
            name: Unique name (e.g. "qdrant", "sqlite").
            provider_class: Class subclassing VectorDBProvider.
        """
        if not issubclass(provider_class, VectorDBProvider):
            raise TypeError(f"{provider_class.__name__} must subclass VectorDBProvider")
        cls._providers[name] = provider_class
        _LOGGER.debug("Registered vector DB provider: %s", name)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> VectorDBProvider:
        """Instantiate a registered vector DB provider.

        Args:
            name: Provider name.
            **kwargs: Constructor arguments.

        Returns:
            Configured VectorDBProvider instance.

        Raises:
            ValueError: If the provider name is unknown.
        """
        if name not in cls._providers:
            available = ", ".join(cls._providers.keys()) or "none"
            raise ValueError(f"Unknown vector DB provider {name!r}. Available: {available}")
        _LOGGER.debug("Creating vector DB provider: %s", name)
        return cls._providers[name](**kwargs)

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return list of registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider name is registered."""
        return name in cls._providers
