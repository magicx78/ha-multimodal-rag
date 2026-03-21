"""Unit tests for document processors."""
from __future__ import annotations

import os
import tempfile

import pytest

from ..processors import ProcessedDocument, ProcessorRegistry
from ..processors.text_processor import process_text_file, _normalize_text


class TestTextNormalization:
    """Tests for _normalize_text helper."""

    def test_normalizes_crlf_line_endings(self):
        """CRLF and CR endings should be converted to LF."""
        result = _normalize_text("line1\r\nline2\rline3")
        assert "\r" not in result
        assert "line1" in result
        assert "line2" in result

    def test_collapses_excessive_blank_lines(self):
        """More than 2 consecutive blank lines should be reduced to 2."""
        result = _normalize_text("a\n\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_preserves_content(self):
        """Normalization must not lose any words."""
        text = "Hello world. This is a test."
        result = _normalize_text(text)
        assert "Hello" in result
        assert "test" in result

    def test_empty_input_returns_empty(self):
        """Empty string should return empty string."""
        assert _normalize_text("") == ""


@pytest.mark.asyncio
class TestTextProcessor:
    """Async tests for process_text_file."""

    async def test_processes_simple_text_file(self, sample_text_file: str):
        """Should return a ProcessedDocument with content for a valid text file."""
        result = await process_text_file(sample_text_file)
        assert isinstance(result, ProcessedDocument)
        assert result.document_type == "text"
        assert result.source_file == sample_text_file
        assert len(result.chunks) == 1  # Short file = single chunk
        assert "Home Assistant" in result.raw_text

    async def test_metadata_contains_file_info(self, sample_text_file: str):
        """Metadata should include source_file, char_count, and word_count."""
        result = await process_text_file(sample_text_file)
        assert result.metadata["source_file"] == sample_text_file
        assert result.metadata["char_count"] > 0
        assert result.metadata["word_count"] > 0

    async def test_processes_markdown_file(self, sample_markdown_file: str):
        """Should handle .md files the same way as .txt."""
        result = await process_text_file(sample_markdown_file)
        assert result.document_type == "text"
        assert "Multimodal RAG" in result.raw_text

    async def test_missing_file_raises(self):
        """Processing a non-existent file should raise OSError."""
        with pytest.raises(OSError):
            await process_text_file("/nonexistent/path/file.txt")

    async def test_empty_file_returns_no_chunks(self, temp_dir: str):
        """Empty file should produce no chunks."""
        empty_file = os.path.join(temp_dir, "empty.txt")
        with open(empty_file, "w") as f:
            f.write("")
        result = await process_text_file(empty_file)
        assert result.chunks == []


class TestProcessorRegistry:
    """Tests for ProcessorRegistry."""

    def test_supported_extensions_not_empty(self):
        """Registry should have at least the text extensions registered."""
        # Import processors to trigger registration
        import custom_components.multimodal_rag.processors.text_processor as _  # noqa: F401
        extensions = ProcessorRegistry.supported_extensions()
        assert len(extensions) > 0

    def test_text_extensions_registered(self):
        """Standard text extensions should be in the registry."""
        import custom_components.multimodal_rag.processors.text_processor as _  # noqa: F401
        assert ProcessorRegistry.get_processor(".txt") is not None
        assert ProcessorRegistry.get_processor(".md") is not None

    def test_unknown_extension_returns_none(self):
        """Unknown extension should return None, not raise."""
        result = ProcessorRegistry.get_processor(".xyz_unknown_extension")
        assert result is None

    def test_register_and_retrieve(self):
        """Custom processor should be retrievable after registration."""
        async def my_processor(path, **kwargs):
            return ProcessedDocument(
                source_file=path, document_type="test", chunks=["test"]
            )

        ProcessorRegistry.register([".mytest_ext"], my_processor)
        retrieved = ProcessorRegistry.get_processor(".mytest_ext")
        assert retrieved is my_processor
