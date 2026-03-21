"""Base class for embedding providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""

    vectors: list[list[float]]
    model: str
    provider: str
    dimension: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate dimension consistency."""
        if self.vectors and len(self.vectors[0]) != self.dimension:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.dimension}, "
                f"got {len(self.vectors[0])}"
            )


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding providers.

    Supports single and batch embedding. Providers self-report
    their output dimension so downstream code can configure
    vector DB collections correctly.
    """

    def __init__(self, model: str, **kwargs: Any) -> None:
        """Initialize with model name and optional config."""
        self.model = model
        self._config = kwargs

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension for this model."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single piece of text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> EmbeddingResult:
        """Embed multiple texts in a single (or batched) API call.

        Implementations should batch efficiently — e.g. Claude allows
        up to 2048 texts per request.

        Args:
            texts: List of text strings to embed.

        Returns:
            EmbeddingResult containing all vectors.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the embedding provider is reachable.

        Returns:
            True if healthy, False otherwise.
        """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r}, dim={self.dimension})"
