"""Integration tests for the RAG Engine."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestRAGEngineInitialization:
    """Tests for RAGEngine initialization."""

    async def test_initialize_creates_collection(self, rag_engine, mock_vector_db):
        """initialize() should create the default collection in the DB."""
        await rag_engine.initialize()
        mock_vector_db.create_collection.assert_called_once()
        call_kwargs = mock_vector_db.create_collection.call_args
        # Collection name should be 'test_collection'
        assert "test_collection" in str(call_kwargs)

    async def test_initialize_creates_storage_dir(self, rag_engine, temp_dir):
        """initialize() should create the storage directory."""
        storage_path = os.path.join(temp_dir, "rag_storage_test")
        rag_engine._storage_path = storage_path
        await rag_engine.initialize()
        assert os.path.exists(storage_path)

    async def test_double_initialize_safe(self, rag_engine):
        """Calling initialize() twice should not raise errors."""
        await rag_engine.initialize()
        await rag_engine.initialize()  # Should not raise


@pytest.mark.asyncio
class TestRAGEngineIndexing:
    """Tests for document indexing pipeline."""

    async def test_index_text_document(self, rag_engine, sample_text_file, mock_vector_db):
        """Should successfully index a text file end-to-end."""
        # Import text processor to register it
        import custom_components.multimodal_rag.processors.text_processor  # noqa: F401

        result = await rag_engine.index_document(sample_text_file)

        assert result.success is True
        assert result.source_file == sample_text_file
        assert result.document_type == "text"
        assert result.chunk_count > 0
        assert result.document_id != ""
        # Vector DB upsert should have been called
        mock_vector_db.upsert.assert_called()

    async def test_index_nonexistent_file_returns_failure(self, rag_engine):
        """Indexing a non-existent file should return a failed IndexResult."""
        import custom_components.multimodal_rag.processors.text_processor  # noqa: F401

        result = await rag_engine.index_document("/nonexistent/file.txt")
        assert result.success is False
        assert result.error != ""

    async def test_index_unsupported_extension_returns_failure(self, rag_engine, temp_dir):
        """Unsupported file type should return a failed IndexResult."""
        bad_file = os.path.join(temp_dir, "file.xyz_bad")
        with open(bad_file, "w") as f:
            f.write("content")
        result = await rag_engine.index_document(bad_file)
        assert result.success is False
        assert "Unsupported" in result.error

    async def test_document_id_is_stable(self, rag_engine, sample_text_file):
        """Same file should always produce the same document ID."""
        import custom_components.multimodal_rag.processors.text_processor  # noqa: F401

        result1 = await rag_engine.index_document(sample_text_file)
        result2 = await rag_engine.index_document(sample_text_file)
        assert result1.document_id == result2.document_id

    async def test_index_with_metadata(self, rag_engine, sample_text_file, mock_vector_db):
        """User metadata should be passed through to DocumentRecords."""
        import custom_components.multimodal_rag.processors.text_processor  # noqa: F401

        result = await rag_engine.index_document(
            sample_text_file,
            metadata={"category": "test", "priority": 1},
        )
        assert result.success is True
        # Check that upsert was called with records containing our metadata
        call_args = mock_vector_db.upsert.call_args[0][0]  # First positional arg
        assert any("category" in r.metadata for r in call_args)


@pytest.mark.asyncio
class TestRAGEngineSearch:
    """Tests for similarity search."""

    async def test_search_returns_search_response(self, rag_engine, sample_text_file):
        """search() should return a SearchResponse object."""
        import custom_components.multimodal_rag.processors.text_processor  # noqa: F401
        from custom_components.multimodal_rag.rag.similarity_search import SearchResponse

        await rag_engine.index_document(sample_text_file)
        response = await rag_engine.search("Home Assistant automation")
        assert isinstance(response, SearchResponse)
        assert response.query == "Home Assistant automation"

    async def test_search_calls_embedding_provider(self, rag_engine, mock_embedding_provider):
        """Search should call the embedding provider to encode the query."""
        await rag_engine.search("test query")
        mock_embedding_provider.embed.assert_called()

    async def test_search_calls_vector_db(self, rag_engine, mock_vector_db):
        """Search should call the vector DB search method."""
        await rag_engine.search("test query")
        mock_vector_db.search.assert_called()


@pytest.mark.asyncio
class TestRAGEngineReasoning:
    """Tests for LLM-based reasoning."""

    async def test_reason_returns_answer(self, rag_engine, sample_text_file):
        """reason() should return a ReasonResult with a non-empty answer."""
        import custom_components.multimodal_rag.processors.text_processor  # noqa: F401
        from custom_components.multimodal_rag.rag.engine import ReasonResult

        await rag_engine.index_document(sample_text_file)
        result = await rag_engine.reason("What is Home Assistant?")

        assert isinstance(result, ReasonResult)
        assert result.answer != ""
        assert result.query == "What is Home Assistant?"

    async def test_reason_calls_llm_provider(self, rag_engine, mock_llm_provider):
        """reason() must invoke the LLM provider's reason() method."""
        await rag_engine.reason("test question")
        mock_llm_provider.reason.assert_called_once()

    async def test_reason_includes_sources(self, rag_engine, sample_text_file):
        """ReasonResult should include source attribution from search."""
        import custom_components.multimodal_rag.processors.text_processor  # noqa: F401

        await rag_engine.index_document(sample_text_file)
        result = await rag_engine.reason("What is Home Assistant?")
        # Sources should be a list (may be empty if no DB results)
        assert isinstance(result.sources, list)


@pytest.mark.asyncio
class TestRAGEngineCollections:
    """Tests for collection management."""

    async def test_list_collections(self, rag_engine, mock_vector_db):
        """list_collections() should delegate to the vector DB."""
        mock_vector_db.list_collections.return_value = ["col_a", "col_b"]
        collections = await rag_engine.list_collections()
        assert "col_a" in collections
        assert "col_b" in collections

    async def test_delete_document(self, rag_engine, mock_vector_db):
        """delete_document() should call the DB delete method."""
        success = await rag_engine.delete_document("doc_123", collection="test")
        mock_vector_db.delete.assert_called_once_with(
            collection="test", document_id="doc_123"
        )
        assert success is True

    async def test_health_check_all_subsystems(
        self, rag_engine, mock_llm_provider, mock_embedding_provider, mock_vector_db
    ):
        """health_check() should return status for all three subsystems."""
        health = await rag_engine.health_check()
        assert "llm" in health
        assert "embedder" in health
        assert "vector_db" in health
        assert all(health.values())  # All mocks return True
