"""Document processor package for Multimodal RAG."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProcessedDocument:
    """Unified output from any document processor."""

    source_file: str
    document_type: str           # "text", "pdf", "image", "audio"
    chunks: list[str]            # Text chunks ready for embedding
    metadata: dict[str, Any] = field(default_factory=dict)
    images: list[bytes] = field(default_factory=list)  # Raw image bytes if extracted
    raw_text: str = ""           # Full extracted text (pre-chunking)

    @property
    def chunk_count(self) -> int:
        """Return number of text chunks."""
        return len(self.chunks)


class ProcessorRegistry:
    """Registry mapping file extensions to processor functions.

    Usage:
        ProcessorRegistry.register([".pdf"], pdf_processor_func)
        processor = ProcessorRegistry.get_processor(".pdf")
    """

    _processors: dict[str, Any] = {}

    @classmethod
    def register(cls, extensions: list[str], processor: Any) -> None:
        """Register a processor callable for given file extensions.

        Args:
            extensions: List of lowercase extensions (e.g. [".pdf", ".PDF"]).
            processor: Async callable(file_path, **kwargs) -> ProcessedDocument.
        """
        for ext in extensions:
            cls._processors[ext.lower()] = processor

    @classmethod
    def get_processor(cls, extension: str) -> Any | None:
        """Return the processor for a given extension.

        Args:
            extension: File extension including dot (e.g. ".pdf").

        Returns:
            Processor callable or None if unsupported.
        """
        return cls._processors.get(extension.lower())

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """Return all registered file extensions."""
        return list(cls._processors.keys())


__all__ = ["ProcessedDocument", "ProcessorRegistry"]
