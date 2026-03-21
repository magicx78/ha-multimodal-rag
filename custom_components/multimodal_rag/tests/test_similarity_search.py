"""Unit tests for SimilaritySearch module."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ..db.base import SearchResult
from ..rag.similarity_search import SearchResponse, SimilaritySearch


def _make_search_result(id: str, score: float, text: str = "test text") -> SearchResult:
    return SearchResult(
        id=id, text=text, score=score,
        metadata={"source_file": f"/docs/{id}.txt"},
        collection="test",
    )


@pytest.mark.asyncio
class TestSimilaritySearch:
    """Tests for SimilaritySearch."""

    def _make_searcher(
        self,
        mock_embedding_provider,
        mock_vector_db,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> SimilaritySearch:
        return SimilaritySearch(
            db=mock_vector_db,
            embedding_provider=mock_embedding_provider,
            default_top_k=top_k,
            default_score_threshold=threshold,
        )

    async def test_search_embeds_query(self, mock_embedding_provider, mock_vector_db):
        """Searching should call the embedding provider exactly once."""
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db)
        await searcher.search("test query", collection="col")
        mock_embedding_provider.embed.assert_called_once_with("test query")

    async def test_search_calls_vector_db(self, mock_embedding_provider, mock_vector_db):
        """Search should invoke vector DB search with the embedded query."""
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db)
        await searcher.search("test query", collection="my_col")
        mock_vector_db.search.assert_called_once()
        call_kwargs = mock_vector_db.search.call_args[1]
        assert call_kwargs["collection"] == "my_col"

    async def test_search_returns_search_response(self, mock_embedding_provider, mock_vector_db):
        """Should return a SearchResponse instance."""
        mock_vector_db.search = AsyncMock(return_value=[
            _make_search_result("doc1", 0.95),
            _make_search_result("doc2", 0.85),
        ])
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db)
        response = await searcher.search("query", collection="col")
        assert isinstance(response, SearchResponse)
        assert response.query == "query"
        assert response.has_results is True

    async def test_deduplication_removes_duplicates(self, mock_embedding_provider, mock_vector_db):
        """Duplicate IDs in results should be deduplicated."""
        mock_vector_db.search = AsyncMock(return_value=[
            _make_search_result("doc1", 0.95),
            _make_search_result("doc1", 0.90),  # Same ID, lower score
            _make_search_result("doc2", 0.80),
        ])
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db, top_k=3)
        response = await searcher.search("query", collection="col")
        ids = [r.id for r in response.results]
        assert ids.count("doc1") == 1  # Deduplicated

    async def test_top_k_limit_applied(self, mock_embedding_provider, mock_vector_db):
        """Results should be limited to top_k."""
        mock_vector_db.search = AsyncMock(return_value=[
            _make_search_result(f"doc{i}", float(10 - i) / 10.0) for i in range(10)
        ])
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db, top_k=3)
        response = await searcher.search("query", collection="col")
        assert len(response.results) <= 3

    async def test_context_built_from_results(self, mock_embedding_provider, mock_vector_db):
        """SearchResponse.context_text should be populated after search."""
        mock_vector_db.search = AsyncMock(return_value=[
            _make_search_result("doc1", 0.9, text="Home Assistant is great."),
        ])
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db)
        response = await searcher.search("query", collection="col")
        assert "Home Assistant is great." in response.context_text
        assert "doc1.txt" in response.context_text  # Source attribution

    async def test_sources_extracted(self, mock_embedding_provider, mock_vector_db):
        """Sources should list unique source files from results."""
        mock_vector_db.search = AsyncMock(return_value=[
            SearchResult(id="a", text="text", score=0.9,
                        metadata={"source_file": "/docs/file1.pdf"}, collection="col"),
            SearchResult(id="b", text="text", score=0.8,
                        metadata={"source_file": "/docs/file1.pdf"}, collection="col"),
            SearchResult(id="c", text="text", score=0.7,
                        metadata={"source_file": "/docs/file2.pdf"}, collection="col"),
        ])
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db, top_k=5)
        response = await searcher.search("query", collection="col")
        response.build_context()
        # Only unique sources
        assert len(response.sources) == 2

    async def test_empty_results_handled_gracefully(self, mock_embedding_provider, mock_vector_db):
        """Empty search results should not raise errors."""
        mock_vector_db.search = AsyncMock(return_value=[])
        searcher = self._make_searcher(mock_embedding_provider, mock_vector_db)
        response = await searcher.search("obscure query", collection="col")
        assert response.has_results is False
        assert response.results == []
        assert response.context_text == ""
