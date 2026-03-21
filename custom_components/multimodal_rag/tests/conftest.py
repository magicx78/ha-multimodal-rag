"""Shared pytest fixtures for Multimodal RAG tests."""
from __future__ import annotations

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Base fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory cleaned up after each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_text_file(temp_dir: str) -> str:
    """Create a small sample text file for testing."""
    file_path = os.path.join(temp_dir, "sample.txt")
    content = (
        "Home Assistant is an open source home automation platform.\n\n"
        "It prioritizes local control and privacy. Powered by a worldwide community "
        "of tinkerers and DIY enthusiasts.\n\n"
        "Perfect to run on a Raspberry Pi or a local server.\n"
    )
    with open(file_path, "w") as f:
        f.write(content)
    return file_path


@pytest.fixture
def sample_markdown_file(temp_dir: str) -> str:
    """Create a sample Markdown file."""
    file_path = os.path.join(temp_dir, "readme.md")
    content = "# Multimodal RAG\n\nA powerful RAG system for Home Assistant.\n\n## Features\n\n- Text search\n- PDF indexing\n- Image understanding\n"
    with open(file_path, "w") as f:
        f.write(content)
    return file_path


# ── Mock LLM Provider ────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Return a mock LLM provider."""
    from custom_components.multimodal_rag.llm.base import LLMProvider, LLMResponse

    provider = MagicMock(spec=LLMProvider)
    provider.model = "mock-model"
    provider.generate = AsyncMock(
        return_value=LLMResponse(
            content="Mock generated response",
            model="mock-model",
            provider="mock",
            usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )
    )
    provider.reason = AsyncMock(
        return_value=LLMResponse(
            content="Mock reasoned answer based on the provided context.",
            model="mock-model",
            provider="mock",
            usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        )
    )
    provider.health_check = AsyncMock(return_value=True)
    return provider


# ── Mock Embedding Provider ──────────────────────────────────────────────────

@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    """Return a mock embedding provider with 4-dimensional vectors."""
    from custom_components.multimodal_rag.embeddings.base import (
        EmbeddingProvider,
        EmbeddingResult,
    )

    MOCK_DIM = 4  # Small dimension for tests

    provider = MagicMock(spec=EmbeddingProvider)
    provider.model = "mock-embed"
    provider.dimension = MOCK_DIM

    async def mock_embed(text: str) -> list[float]:
        # Deterministic vector based on text length
        base = float(len(text) % 10) / 10.0
        return [base, base + 0.1, base + 0.2, base + 0.3]

    async def mock_embed_batch(texts: list[str]) -> EmbeddingResult:
        vectors = []
        for text in texts:
            base = float(len(text) % 10) / 10.0
            vectors.append([base, base + 0.1, base + 0.2, base + 0.3])
        return EmbeddingResult(
            vectors=vectors,
            model="mock-embed",
            provider="mock",
            dimension=MOCK_DIM,
        )

    provider.embed = AsyncMock(side_effect=mock_embed)
    provider.embed_batch = AsyncMock(side_effect=mock_embed_batch)
    provider.health_check = AsyncMock(return_value=True)
    return provider


# ── Mock Vector DB ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_vector_db() -> MagicMock:
    """Return a mock vector database provider with in-memory storage."""
    from custom_components.multimodal_rag.db.base import (
        DocumentRecord,
        SearchResult,
        VectorDBProvider,
    )

    storage: dict[str, dict[str, DocumentRecord]] = {}

    provider = MagicMock(spec=VectorDBProvider)

    async def create_collection(name, dimension, distance="cosine"):
        storage.setdefault(name, {})

    async def delete_collection(name):
        storage.pop(name, None)

    async def list_collections():
        return list(storage.keys())

    async def upsert(records):
        for record in records:
            storage.setdefault(record.collection, {})[record.id] = record

    async def search(collection, vector, top_k=5, score_threshold=0.0, filter_metadata=None):
        records = list(storage.get(collection, {}).values())
        results = [
            SearchResult(
                id=r.id,
                text=r.text,
                score=0.9,  # Mock high score
                metadata=r.metadata,
                collection=collection,
            )
            for r in records[:top_k]
        ]
        return results

    async def delete(collection, document_id):
        storage.get(collection, {}).pop(document_id, None)

    async def get(collection, document_id):
        return storage.get(collection, {}).get(document_id)

    async def health_check():
        return True

    provider.create_collection = AsyncMock(side_effect=create_collection)
    provider.delete_collection = AsyncMock(side_effect=delete_collection)
    provider.list_collections = AsyncMock(side_effect=list_collections)
    provider.upsert = AsyncMock(side_effect=upsert)
    provider.search = AsyncMock(side_effect=search)
    provider.delete = AsyncMock(side_effect=delete)
    provider.get = AsyncMock(side_effect=get)
    provider.health_check = AsyncMock(side_effect=health_check)

    return provider


# ── RAG Engine fixture ───────────────────────────────────────────────────────

@pytest.fixture
def rag_engine(mock_llm_provider, mock_embedding_provider, mock_vector_db, temp_dir):
    """Return a RAG engine with all mock providers."""
    from custom_components.multimodal_rag.rag.engine import RAGEngine

    engine = RAGEngine(
        llm_provider=mock_llm_provider,
        embedding_provider=mock_embedding_provider,
        vector_db=mock_vector_db,
        default_collection="test_collection",
        storage_path=temp_dir,
        chunk_size=500,
        chunk_overlap=50,
    )
    return engine
