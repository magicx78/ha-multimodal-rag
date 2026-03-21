"""Unit tests for the SQLite vector DB provider."""
from __future__ import annotations

import os
import tempfile

import pytest

from ..db.base import DocumentRecord, SearchResult
from ..db.sqlite_db import SQLiteVectorProvider, _cosine_similarity


class TestCosineSimilarity:
    """Tests for the cosine similarity helper."""

    def test_identical_vectors_score_one(self):
        """Identical vectors should yield cosine similarity of 1.0."""
        v = [1.0, 0.0, 0.5]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors_score_zero(self):
        """Orthogonal vectors should yield cosine similarity of 0.0."""
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert abs(_cosine_similarity(v1, v2)) < 1e-6

    def test_zero_vector_returns_zero(self):
        """Zero vector should not cause division by zero."""
        v1 = [0.0, 0.0]
        v2 = [1.0, 2.0]
        assert _cosine_similarity(v1, v2) == 0.0


@pytest.mark.asyncio
class TestSQLiteVectorProvider:
    """Integration tests for SQLiteVectorProvider."""

    def _make_provider(self, temp_dir: str) -> SQLiteVectorProvider:
        db_path = os.path.join(temp_dir, "test_vectors.db")
        return SQLiteVectorProvider(db_path=db_path)

    async def test_health_check(self, temp_dir: str):
        """Health check should return True for a valid SQLite file."""
        provider = self._make_provider(temp_dir)
        assert await provider.health_check() is True

    async def test_create_and_list_collections(self, temp_dir: str):
        """Creating a collection should make it appear in list_collections."""
        provider = self._make_provider(temp_dir)
        await provider.create_collection("my_col", dimension=4)
        collections = await provider.list_collections()
        assert "my_col" in collections

    async def test_upsert_and_get(self, temp_dir: str):
        """Upserting a record and retrieving it by ID should work."""
        provider = self._make_provider(temp_dir)
        await provider.create_collection("col1", dimension=4)

        record = DocumentRecord(
            id="doc1",
            text="Test document text",
            vector=[0.1, 0.2, 0.3, 0.4],
            metadata={"source": "test.txt"},
            collection="col1",
        )
        await provider.upsert([record])

        retrieved = await provider.get("col1", "doc1")
        assert retrieved is not None
        assert retrieved.id == "doc1"
        assert retrieved.text == "Test document text"
        assert retrieved.metadata["source"] == "test.txt"

    async def test_upsert_updates_existing(self, temp_dir: str):
        """Upserting the same ID twice should update, not duplicate."""
        provider = self._make_provider(temp_dir)
        await provider.create_collection("col1", dimension=4)

        record = DocumentRecord(
            id="doc1", text="Original", vector=[0.1, 0.2, 0.3, 0.4], collection="col1"
        )
        await provider.upsert([record])

        updated = DocumentRecord(
            id="doc1", text="Updated", vector=[0.5, 0.6, 0.7, 0.8], collection="col1"
        )
        await provider.upsert([updated])

        retrieved = await provider.get("col1", "doc1")
        assert retrieved.text == "Updated"

    async def test_search_returns_results(self, temp_dir: str):
        """Searching should return records sorted by cosine similarity."""
        provider = self._make_provider(temp_dir)
        await provider.create_collection("col1", dimension=4)

        records = [
            DocumentRecord(
                id=f"doc{i}", text=f"Document {i}",
                vector=[float(i) / 10, 0.1, 0.2, 0.3],
                collection="col1",
            )
            for i in range(5)
        ]
        await provider.upsert(records)

        query_vector = [0.4, 0.1, 0.2, 0.3]  # Closest to doc4
        results = await provider.search("col1", query_vector, top_k=3)

        assert len(results) <= 3
        assert all(isinstance(r, SearchResult) for r in results)
        # Results should be sorted by score descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    async def test_delete_removes_record(self, temp_dir: str):
        """Deleting a record should make it unretrievable."""
        provider = self._make_provider(temp_dir)
        await provider.create_collection("col1", dimension=4)

        record = DocumentRecord(
            id="to_delete", text="Delete me", vector=[0.1, 0.2, 0.3, 0.4], collection="col1"
        )
        await provider.upsert([record])
        await provider.delete("col1", "to_delete")

        retrieved = await provider.get("col1", "to_delete")
        assert retrieved is None

    async def test_delete_collection(self, temp_dir: str):
        """Deleting a collection should remove it from list_collections."""
        provider = self._make_provider(temp_dir)
        await provider.create_collection("temp_col", dimension=4)
        await provider.delete_collection("temp_col")

        collections = await provider.list_collections()
        assert "temp_col" not in collections

    async def test_search_empty_collection_returns_empty(self, temp_dir: str):
        """Searching an empty or non-existent collection should return []."""
        provider = self._make_provider(temp_dir)
        results = await provider.search("nonexistent_col", [0.1, 0.2, 0.3, 0.4])
        assert results == []

    async def test_score_threshold_filters_results(self, temp_dir: str):
        """score_threshold should filter out low-scoring results."""
        provider = self._make_provider(temp_dir)
        await provider.create_collection("col1", dimension=2)

        # Add one similar and one dissimilar record
        await provider.upsert([
            DocumentRecord(id="sim", text="similar", vector=[1.0, 0.0], collection="col1"),
            DocumentRecord(id="diff", text="different", vector=[0.0, 1.0], collection="col1"),
        ])

        # Query vector pointing in [1,0] direction → "sim" should score ~1.0
        results = await provider.search("col1", [1.0, 0.0], score_threshold=0.9)
        # Only the similar document should pass the threshold
        ids = [r.id for r in results]
        assert "sim" in ids
        assert "diff" not in ids
