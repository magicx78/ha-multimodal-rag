"""Plain text and Markdown document processor."""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

import aiofiles

from . import ProcessedDocument, ProcessorRegistry

_LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = [".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml"]


async def process_text_file(file_path: str, **kwargs: Any) -> ProcessedDocument:
    """Load and normalize a plain text file.

    Reads the file asynchronously, strips excessive whitespace,
    and returns the content as a single raw chunk. Chunking into
    fixed-size pieces is handled by the RAG chunker.

    Args:
        file_path: Absolute path to the text file.
        **kwargs: Optional arguments (encoding, etc.).

    Returns:
        ProcessedDocument with raw text and single chunk.
    """
    encoding = kwargs.get("encoding", "utf-8")

    try:
        async with aiofiles.open(file_path, encoding=encoding, errors="replace") as fh:
            raw_text = await fh.read()
    except OSError as exc:
        _LOGGER.error("Failed to read text file %r: %s", file_path, exc)
        raise

    # Basic normalization
    normalized = _normalize_text(raw_text)

    file_name = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    metadata = {
        "source_file": file_path,
        "file_name": file_name,
        "document_type": "text",
        "extension": ext,
        "char_count": len(normalized),
        "word_count": len(normalized.split()),
    }

    _LOGGER.info(
        "Processed text file %r: %d chars, %d words",
        file_name, metadata["char_count"], metadata["word_count"],
    )

    return ProcessedDocument(
        source_file=file_path,
        document_type="text",
        chunks=[normalized] if normalized else [],
        metadata=metadata,
        raw_text=normalized,
    )


def _normalize_text(text: str) -> str:
    """Normalize text by removing excessive whitespace.

    Args:
        text: Raw input text.

    Returns:
        Cleaned text string.
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse sequences of 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


# Register processor
ProcessorRegistry.register(SUPPORTED_EXTENSIONS, process_text_file)
