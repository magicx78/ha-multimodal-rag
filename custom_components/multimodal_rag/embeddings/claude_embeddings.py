"""Claude (Voyage) embedding provider implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .base import EmbeddingProvider, EmbeddingResult
from .factory import EmbeddingFactory

_LOGGER = logging.getLogger(__name__)

# Voyage embedding dimensions by model
_VOYAGE_DIMENSIONS: dict[str, int] = {
    "voyage-3-large": 3072,
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 2048,
    "voyage-finance-2": 1024,
    "voyage-multilingual-2": 1024,
}

# Claude/Anthropic API has a max batch size for embeddings
_MAX_BATCH_SIZE = 128


class ClaudeEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Anthropic's Voyage embedding models.

    Voyage models are the state-of-the-art embedding models from Anthropic.
    Accessed via the anthropic client's embed endpoint.
    """

    def __init__(
        self,
        model: str = "voyage-3-large",
        api_key: str = "",
        input_type: str = "document",
        **kwargs: Any,
    ) -> None:
        """Initialize the Claude embedding provider.

        Args:
            model: Voyage model name.
            api_key: Anthropic API key.
            input_type: "document" for indexing, "query" for search queries.
        """
        super().__init__(model=model, **kwargs)
        self._api_key = api_key
        self._input_type = input_type
        self._client: Any = None

    @property
    def dimension(self) -> int:
        """Return vector dimension for the configured model."""
        return _VOYAGE_DIMENSIONS.get(self.model, 3072)

    def _get_client(self) -> Any:
        """Lazily create the Anthropic client."""
        if self._client is None:
            try:
                import anthropic  # noqa: PLC0415
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError as exc:
                raise ImportError(
                    "anthropic package is required. pip install anthropic"
                ) from exc
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        result = await self.embed_batch([text])
        return result.vectors[0]

    async def embed_batch(self, texts: list[str]) -> EmbeddingResult:
        """Embed multiple texts with automatic batching.

        Splits large lists into chunks of _MAX_BATCH_SIZE and
        makes multiple API calls if needed.

        Args:
            texts: List of texts to embed.

        Returns:
            EmbeddingResult with all vectors in original order.
        """
        if not texts:
            return EmbeddingResult(
                vectors=[], model=self.model, provider="claude", dimension=self.dimension
            )

        client = self._get_client()
        all_vectors: list[list[float]] = []

        # Split into batches
        batches = [
            texts[i : i + _MAX_BATCH_SIZE]
            for i in range(0, len(texts), _MAX_BATCH_SIZE)
        ]

        for batch in batches:
            try:
                # Run in executor since anthropic client is sync
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda b=batch: client.embeddings.create(
                        model=self.model,
                        input=b,
                        input_type=self._input_type,
                    ),
                )
                batch_vectors = [item.embedding for item in response.data]
                all_vectors.extend(batch_vectors)
                _LOGGER.debug(
                    "Claude embeddings batch: %d texts embedded (model=%s)",
                    len(batch), self.model,
                )
            except Exception as exc:
                _LOGGER.error("Claude embedding batch error: %s", exc)
                raise

        return EmbeddingResult(
            vectors=all_vectors,
            model=self.model,
            provider="claude",
            dimension=self.dimension,
        )

    async def health_check(self) -> bool:
        """Verify Claude embedding API is accessible."""
        try:
            vector = await self.embed("health check")
            return len(vector) == self.dimension
        except Exception as exc:
            _LOGGER.warning("Claude embedding health check failed: %s", exc)
            return False


# Auto-register
EmbeddingFactory.register("claude", ClaudeEmbeddingProvider)
