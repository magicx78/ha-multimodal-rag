"""Base classes for vector database providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentRecord:
    """A document chunk stored in the vector database."""

    id: str
    text: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    collection: str = "documents"

    # Convenience accessors for common metadata fields
    @property
    def source_file(self) -> str:
        """Return original file path if available."""
        return self.metadata.get("source_file", "")

    @property
    def document_type(self) -> str:
        """Return document type (pdf, image, text, etc.)."""
        return self.metadata.get("document_type", "unknown")


@dataclass
class SearchResult:
    """A search result from the vector database."""

    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    collection: str = "documents"

    @property
    def source_file(self) -> str:
        """Return original file path."""
        return self.metadata.get("source_file", "")


class VectorDBProvider(ABC):
    """Abstract base class for vector database backends.

    Implementations must support CRUD on document records and
    similarity search. The collection concept maps to a logical
    namespace (e.g. a Qdrant collection or SQLite table).
    """

    @abstractmethod
    async def create_collection(
        self, name: str, dimension: int, distance: str = "cosine"
    ) -> None:
        """Create a new vector collection if it does not exist.

        Args:
            name: Collection name.
            dimension: Embedding vector dimension.
            distance: Distance metric ("cosine", "dot", "euclidean").
        """

    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        """Delete a collection and all its vectors.

        Args:
            name: Collection name to delete.
        """

    @abstractmethod
    async def list_collections(self) -> list[str]:
        """Return all collection names.

        Returns:
            List of collection name strings.
        """

    @abstractmethod
    async def upsert(self, records: list[DocumentRecord]) -> None:
        """Insert or update document records in the database.

        Args:
            records: List of DocumentRecord objects to upsert.
        """

    @abstractmethod
    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Find the top-K most similar documents.

        Args:
            collection: Collection to search.
            vector: Query embedding vector.
            top_k: Maximum number of results.
            score_threshold: Minimum similarity score (0.0–1.0).
            filter_metadata: Optional metadata filters.

        Returns:
            List of SearchResult sorted by descending score.
        """

    @abstractmethod
    async def delete(self, collection: str, document_id: str) -> None:
        """Delete a single document record.

        Args:
            collection: Collection containing the document.
            document_id: Unique document ID.
        """

    @abstractmethod
    async def get(self, collection: str, document_id: str) -> DocumentRecord | None:
        """Retrieve a document record by ID.

        Args:
            collection: Collection name.
            document_id: Document ID.

        Returns:
            DocumentRecord or None if not found.
        """

    @abstractmethod
    async def list_documents(self, collection: str) -> list[dict]:
        """Return a summary of all unique documents in a collection.

        Groups chunks by document_id and returns one record per logical document.

        Args:
            collection: Collection name.

        Returns:
            List of dicts with keys: document_id, source_file, document_type, chunk_count.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the database is reachable.

        Returns:
            True if healthy, False otherwise.
        """
