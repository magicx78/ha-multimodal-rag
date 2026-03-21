"""Document processing coordination module for the RAG pipeline.

This module acts as the bridge between the document processors
(PDF, image, text) and the RAG engine, providing a unified
processing interface with validation and error handling.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from ..processors import ProcessedDocument, ProcessorRegistry
from ..const import (
    SUPPORTED_TEXT_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
)

_LOGGER = logging.getLogger(__name__)

ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_TEXT_EXTENSIONS
    + SUPPORTED_PDF_EXTENSIONS
    + SUPPORTED_IMAGE_EXTENSIONS
    + SUPPORTED_AUDIO_EXTENSIONS
    + SUPPORTED_VIDEO_EXTENSIONS
)


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""


async def process_document(
    file_path: str,
    extra_kwargs: dict[str, Any] | None = None,
) -> ProcessedDocument:
    """Route a file to the correct processor and return a ProcessedDocument.

    This is the single entry point for the RAG engine to process any
    supported file type. It validates the file, selects the processor,
    and handles errors uniformly.

    Args:
        file_path: Absolute path to the file.
        extra_kwargs: Additional kwargs forwarded to the processor
                      (e.g. api_key for image vision processing).

    Returns:
        ProcessedDocument ready for chunking and embedding.

    Raises:
        DocumentProcessingError: If the file is missing, unsupported,
                                  or processing fails.
    """
    if not os.path.exists(file_path):
        raise DocumentProcessingError(f"File not found: {file_path}")

    if not os.path.isfile(file_path):
        raise DocumentProcessingError(f"Path is not a file: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if not ext:
        raise DocumentProcessingError(
            f"Cannot determine file type (no extension): {file_path}"
        )

    processor = ProcessorRegistry.get_processor(ext)
    if processor is None:
        raise DocumentProcessingError(
            f"Unsupported file type {ext!r}. "
            f"Supported: {', '.join(ProcessorRegistry.supported_extensions())}"
        )

    kwargs = extra_kwargs or {}

    try:
        _LOGGER.debug("Processing %r with %s", file_path, processor.__name__)
        result = await processor(file_path, **kwargs)
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(
            f"Processing failed for {file_path!r}: {exc}"
        ) from exc

    if not result.chunks and not result.raw_text:
        _LOGGER.warning("Processor returned empty result for %r", file_path)

    return result


def get_document_type(file_path: str) -> str:
    """Determine document type from file extension.

    Args:
        file_path: File path or filename.

    Returns:
        Type string: "text", "pdf", "image", "audio", "video", or "unknown".
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_TEXT_EXTENSIONS:
        return "text"
    if ext in SUPPORTED_PDF_EXTENSIONS:
        return "pdf"
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    if ext in SUPPORTED_AUDIO_EXTENSIONS:
        return "audio"
    if ext in SUPPORTED_VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def is_supported_file(file_path: str) -> bool:
    """Check whether a file extension is supported.

    Args:
        file_path: File path or filename.

    Returns:
        True if the file type has a registered processor.
    """
    ext = os.path.splitext(file_path)[1].lower()
    return ProcessorRegistry.get_processor(ext) is not None
