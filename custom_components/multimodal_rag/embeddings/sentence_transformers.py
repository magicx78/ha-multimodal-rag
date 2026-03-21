"""Sentence-Transformers embedding provider (local fallback)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .base import EmbeddingProvider, EmbeddingResult
from .factory import EmbeddingFactory

_LOGGER = logging.getLogger(__name__)

# Known dimensions for common sentence-transformer models
_MODEL_DIMENSIONS: dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "all-MiniLM-L12-v2": 384,
    "all-mpnet-base-v2": 768,
    "paraphrase-multilingual-MiniLM-L12-v2": 384,
    "multi-qa-MiniLM-L6-cos-v1": 384,
    "all-distilroberta-v1": 768,
}

_DEFAULT_BATCH_SIZE = 64


class SentenceTransformerProvider(EmbeddingProvider):
    """Embedding provider using local Sentence-Transformers models.

    Runs entirely offline — ideal as a fallback when Claude API
    is unavailable. Supports GPU acceleration when available.
    """

    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        device: str = "auto",
        batch_size: int = _DEFAULT_BATCH_SIZE,
        **kwargs: Any,
    ) -> None:
        """Initialize the Sentence-Transformers provider.

        Args:
            model: HuggingFace model name or path.
            device: "cpu", "cuda", or "auto" (auto-detect GPU).
            batch_size: Batch size for encoding.
        """
        super().__init__(model=model, **kwargs)
        self._device = device
        self._batch_size = batch_size
        self._model_instance: Any = None
        self._actual_dim: int | None = None

    @property
    def dimension(self) -> int:
        """Return embedding dimension (introspects model if needed)."""
        if self._actual_dim is not None:
            return self._actual_dim
        return _MODEL_DIMENSIONS.get(self.model, 384)

    def _load_model(self) -> Any:
        """Load and cache the SentenceTransformer model."""
        if self._model_instance is None:
            try:
                from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers package is required. "
                    "pip install sentence-transformers"
                ) from exc

            device = self._device
            if device == "auto":
                try:
                    import torch  # noqa: PLC0415
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"

            _LOGGER.info(
                "Loading SentenceTransformer model %r on device %r", self.model, device
            )
            self._model_instance = SentenceTransformer(self.model, device=device)
            # Cache actual dimension
            self._actual_dim = self._model_instance.get_sentence_embedding_dimension()
            _LOGGER.info(
                "Model loaded: %r — dimension=%d", self.model, self._actual_dim
            )
        return self._model_instance

    async def embed(self, text: str) -> list[float]:
        """Embed a single text using SentenceTransformers.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector.
        """
        result = await self.embed_batch([text])
        return result.vectors[0]

    async def embed_batch(self, texts: list[str]) -> EmbeddingResult:
        """Embed multiple texts using batch encoding.

        Runs CPU-intensive encoding in a thread pool to avoid
        blocking the Home Assistant event loop.

        Args:
            texts: List of texts to embed.

        Returns:
            EmbeddingResult with all vectors.
        """
        if not texts:
            return EmbeddingResult(
                vectors=[], model=self.model, provider="sentence_transformers",
                dimension=self.dimension,
            )

        loop = asyncio.get_event_loop()

        def _encode() -> list[list[float]]:
            model = self._load_model()
            embeddings = model.encode(
                texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embeddings.tolist()

        try:
            vectors = await loop.run_in_executor(None, _encode)
            _LOGGER.debug(
                "SentenceTransformers: embedded %d texts (model=%s)", len(texts), self.model
            )
            return EmbeddingResult(
                vectors=vectors,
                model=self.model,
                provider="sentence_transformers",
                dimension=self.dimension,
            )
        except Exception as exc:
            _LOGGER.error("SentenceTransformers embedding error: %s", exc)
            raise

    async def health_check(self) -> bool:
        """Verify the model can be loaded and produces valid output."""
        try:
            vector = await self.embed("health check")
            return len(vector) == self.dimension
        except Exception as exc:
            _LOGGER.warning("SentenceTransformers health check failed: %s", exc)
            return False


# Auto-register
EmbeddingFactory.register("sentence_transformers", SentenceTransformerProvider)
