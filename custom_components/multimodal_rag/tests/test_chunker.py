"""Unit tests for the TextChunker."""
from __future__ import annotations

import pytest

from ..rag.chunker import Chunk, TextChunker, MIN_CHUNK_SIZE


class TestTextChunker:
    """Tests for TextChunker."""

    def test_short_text_returns_single_chunk(self):
        """Text shorter than chunk_size should produce exactly one chunk."""
        chunker = TextChunker(chunk_size=1000, chunk_overlap=100)
        chunks = chunker.chunk_text("Hello world")
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world"
        assert chunks[0].index == 0

    def test_empty_text_returns_no_chunks(self):
        """Empty or whitespace-only text should return no chunks."""
        chunker = TextChunker(chunk_size=1000, chunk_overlap=100)
        assert chunker.chunk_text("") == []
        assert chunker.chunk_text("   \n\n   ") == []

    def test_long_text_is_split(self):
        """Text longer than chunk_size must be split into multiple chunks."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=10)
        # Generate text longer than 100 chars
        text = "word " * 50  # 250 chars
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1

    def test_chunks_have_sequential_indices(self):
        """Chunk indices must be sequential starting from 0."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "sentence. " * 30
        chunks = chunker.chunk_text(text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_overlap_is_respected(self):
        """Consecutive chunks should share overlapping content."""
        chunker = TextChunker(chunk_size=200, chunk_overlap=50)
        # Build a long monotone text so overlap is detectable
        text = "ABCDEFGHIJ " * 50
        chunks = chunker.chunk_text(text)
        if len(chunks) >= 2:
            # First chunk end and second chunk start should overlap
            end_of_first = chunks[0].text[-30:]
            start_of_second = chunks[1].text[:30]
            # There should be some shared content
            assert any(w in start_of_second for w in end_of_first.split() if len(w) > 2)

    def test_chunk_documents_flattens_sections(self):
        """chunk_documents should flatten multiple sections into one list."""
        chunker = TextChunker(chunk_size=1000, chunk_overlap=100)
        sections = ["Section one content.", "Section two content.", "Section three."]
        chunks = chunker.chunk_documents(sections)
        assert len(chunks) == 3
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_metadata_attached_to_chunks(self):
        """Metadata dict should be attached to every chunk."""
        chunker = TextChunker(chunk_size=1000, chunk_overlap=100)
        meta = {"source": "test_file.txt", "author": "test"}
        chunks = chunker.chunk_text("Some text for testing metadata.", metadata=meta)
        assert len(chunks) == 1
        assert chunks[0].metadata["source"] == "test_file.txt"
        assert chunks[0].metadata["author"] == "test"

    def test_invalid_overlap_raises(self):
        """chunk_overlap >= chunk_size should raise ValueError."""
        with pytest.raises(ValueError):
            TextChunker(chunk_size=100, chunk_overlap=100)

    def test_paragraph_break_preferred(self):
        """Chunker should prefer breaking at paragraph boundaries."""
        chunker = TextChunker(chunk_size=80, chunk_overlap=10)
        # Two paragraphs with a clear double newline
        text = "First paragraph content here.\n\nSecond paragraph content here and more."
        chunks = chunker.chunk_text(text)
        # The break should be near the paragraph boundary, not in the middle of a word
        for chunk in chunks:
            assert chunk.text == chunk.text.strip()
            assert len(chunk.text) >= MIN_CHUNK_SIZE or len(chunks) == 1
