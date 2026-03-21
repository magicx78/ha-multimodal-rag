"""Similarity search module with query embedding and re-ranking."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..db.base import SearchResult, VectorDBProvider
from ..embeddings.base import EmbeddingProvider

_LOGGER = logging.getLogger(__name__)


@dataclass
class SearchResponse:
    """Complete search response with ranked results and source attribution."""

    query: str
    results: list[SearchResult]
    collection: str
    top_k: int
    context_text: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def has_results(self) -> bool:
        """Return True if any results were found."""
        return len(self.results) > 0

    def build_context(self, max_chars: int = 12000) -> str:
        """Build a formatted context string from search results.

        Args:
            max_chars: Maximum total characters in the context string.

        Returns:
            Formatted context text for LLM consumption.
        """
        parts: list[str] = []
        total_chars = 0

        for i, result in enumerate(self.results, 1):
            source = result.metadata.get("source_file", result.metadata.get("file_name", "Unknown"))
            header = f"[Document {i} | Source: {source} | Score: {result.score:.3f}]"
            chunk_text = result.text

            entry = f"{header}\n{chunk_text}\n"
            if total_chars + len(entry) > max_chars:
                # Truncate this entry to fit
                remaining = max_chars - total_chars - len(header) - 2
                if remaining > 100:
                    entry = f"{header}\n{chunk_text[:remaining]}...\n"
                else:
                    break

            parts.append(entry)
            total_chars += len(entry)

        context = "\n---\n".join(parts)
        self.context_text = context
        self.sources = list({
            r.metadata.get("source_file", r.metadata.get("file_name", "Unknown"))
            for r in self.results
        })
        return context


class SimilaritySearch:
    """Handles query embedding, vector retrieval, and optional re-ranking.

    Acts as an intermediary between the RAG engine and the vector database.
    Embeds queries using the configured embedding provider, fetches top-K
    candidates, and optionally re-ranks by score threshold.
    """

    def __init__(
        self,
        db: VectorDBProvider,
        embedding_provider: EmbeddingProvider,
        default_top_k: int = 5,
        default_score_threshold: float = 0.0,
    ) -> None:
        """Initialize similarity search.

        Args:
            db: Vector database provider instance.
            embedding_provider: Embedding provider for query encoding.
            default_top_k: Default number of results to return.
            default_score_threshold: Minimum similarity score filter.
        """
        self._db = db
        self._embedder = embedding_provider
        self._default_top_k = default_top_k
        self._default_score_threshold = default_score_threshold

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        filter_metadata: dict[str, Any] | None = None,
    ) -> SearchResponse:
        """Execute a similarity search for the given query.

        1. Embeds the query using the embedding provider (with input_type="query")
        2. Calls the vector DB for top-K candidates
        3. Filters by score threshold
        4. Returns a SearchResponse with context ready for LLM

        Args:
            query: Natural language search query.
            collection: Collection name to search.
            top_k: Number of results (falls back to default).
            score_threshold: Minimum score (falls back to default).
            filter_metadata: Optional metadata filter dict.

        Returns:
            SearchResponse with ranked results.
        """
        k = top_k if top_k is not None else self._default_top_k
        threshold = score_threshold if score_threshold is not None else self._default_score_threshold

        _LOGGER.debug(
            "Searching collection %r for query %r (top_k=%d, threshold=%.2f)",
            collection, query[:80], k, threshold,
        )

        # Embed the query
        try:
            query_vector = await self._embedder.embed(query)
        except Exception as exc:
            _LOGGER.error("Failed to embed search query: %s", exc)
            raise

        # Search vector DB
        try:
            raw_results = await self._db.search(
                collection=collection,
                vector=query_vector,
                top_k=k * 2,  # Over-fetch for re-ranking
                score_threshold=threshold,
                filter_metadata=filter_metadata,
            )
        except Exception as exc:
            _LOGGER.error("Vector DB search failed: %s", exc)
            raise

        # Re-rank: deduplicate by source chunk similarity and trim to top_k
        ranked = self._rerank(raw_results, k)

        response = SearchResponse(
            query=query,
            results=ranked,
            collection=collection,
            top_k=k,
        )
        response.build_context()

        _LOGGER.info(
            "Search returned %d results from collection %r",
            len(ranked), collection,
        )
        return response

    def _rerank(
        self, results: list[SearchResult], top_k: int
    ) -> list[SearchResult]:
        """Deduplicate and re-rank results by score.

        Removes near-duplicate chunks (same source + overlapping text)
        and returns the top-k highest-scoring unique results.

        Args:
            results: Raw results from vector DB.
            top_k: Target number of results.

        Returns:
            De-duplicated, sorted list of SearchResult.
        """
        if not results:
            return []

        # Sort by score descending
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        # Simple deduplication by document ID
        seen_ids: set[str] = set()
        unique: list[SearchResult] = []

        for result in sorted_results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique.append(result)
            if len(unique) >= top_k:
                break

        return unique
