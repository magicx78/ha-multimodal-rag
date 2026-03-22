"""RAG Engine — main orchestrator for document indexing and querying."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..db.base import DocumentRecord, VectorDBProvider
from ..embeddings.base import EmbeddingProvider
from ..llm.base import LLMProvider, LLMResponse
from ..processors import ProcessedDocument, ProcessorRegistry
from .chunker import TextChunker
from .similarity_search import SearchResponse, SimilaritySearch

_LOGGER = logging.getLogger(__name__)


@dataclass
class IndexResult:
    """Result of a document indexing operation."""

    document_id: str
    source_file: str
    document_type: str
    chunk_count: int
    collection: str
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str = ""


@dataclass
class ReasonResult:
    """Result of an LLM reasoning operation over retrieved context."""

    answer: str
    query: str
    sources: list[str]
    model: str
    provider: str
    search_results_count: int
    usage: dict[str, int] = field(default_factory=dict)


class RAGEngine:
    """Main RAG orchestrator — coordinates all subsystems.

    Pipeline for indexing:
        file_path → processor → chunker → embedder → vector_db

    Pipeline for querying:
        query → embedder → vector_db → context → LLM → answer

    This class is instantiated once per Home Assistant config entry
    and shared across all service calls.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_db: VectorDBProvider,
        default_collection: str = "documents",
        storage_path: str = "/config/multimodal_rag",
        chunk_size: int = 8000,
        chunk_overlap: int = 400,
        default_top_k: int = 5,
        default_score_threshold: float = 0.0,
    ) -> None:
        """Initialize the RAG engine.

        Args:
            llm_provider: LLM provider for answer generation.
            embedding_provider: Embedding provider for vectorization.
            vector_db: Vector database for storage and retrieval.
            default_collection: Default collection name.
            storage_path: Base path for file storage.
            chunk_size: Text chunk size in characters.
            chunk_overlap: Overlap between chunks.
            default_top_k: Default number of search results.
            default_score_threshold: Minimum similarity score.
        """
        self._llm = llm_provider
        self._embedder = embedding_provider
        self._db = vector_db
        self._default_collection = default_collection
        self._storage_path = storage_path

        self._chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._searcher = SimilaritySearch(
            db=vector_db,
            embedding_provider=embedding_provider,
            default_top_k=default_top_k,
            default_score_threshold=default_score_threshold,
        )

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the engine: create storage dirs and DB collections."""
        os.makedirs(self._storage_path, exist_ok=True)

        # Ensure default collection exists with correct dimensions
        try:
            await self._db.create_collection(
                name=self._default_collection,
                dimension=self._embedder.dimension,
                distance="cosine",
            )
            _LOGGER.info(
                "RAG Engine initialized (collection=%r, dim=%d)",
                self._default_collection, self._embedder.dimension,
            )
        except Exception as exc:
            _LOGGER.error("Failed to initialize vector DB collection: %s", exc)
            raise

        self._initialized = True

    async def index_document(
        self,
        file_path: str,
        collection: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IndexResult:
        """Index a document into the RAG system.

        Full pipeline: detect type → process → chunk → embed → store.

        Args:
            file_path: Absolute path to the document file.
            collection: Target collection (uses default if None).
            metadata: Additional user-provided metadata.

        Returns:
            IndexResult with indexing statistics.
        """
        if not self._initialized:
            await self.initialize()

        target_collection = collection or self._default_collection
        extra_meta = metadata or {}

        # Detect file type and select processor
        ext = os.path.splitext(file_path)[1].lower()
        processor = ProcessorRegistry.get_processor(ext)

        if processor is None:
            return IndexResult(
                document_id="",
                source_file=file_path,
                document_type="unknown",
                chunk_count=0,
                collection=target_collection,
                success=False,
                error=f"Unsupported file type: {ext}",
            )

        # Generate stable document ID from file path + content hash
        doc_id = self._generate_document_id(file_path)

        try:
            # Step 1: Process document
            _LOGGER.info("Processing document: %r", file_path)
            processor_kwargs: dict[str, Any] = {}
            if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"):
                # Pass Claude API key for vision processing if available
                from ..llm.claude import ClaudeProvider  # noqa: PLC0415
                if isinstance(self._llm, ClaudeProvider):
                    processor_kwargs["api_key"] = self._llm._api_key
                    processor_kwargs["model"] = self._llm.model

            processed: ProcessedDocument = await processor(file_path, **processor_kwargs)

            if not processed.chunks:
                return IndexResult(
                    document_id=doc_id,
                    source_file=file_path,
                    document_type=processed.document_type,
                    chunk_count=0,
                    collection=target_collection,
                    success=False,
                    error="No content extracted from document",
                )

            # Step 2: Chunk (re-chunk large sections)
            chunk_objects = self._chunker.chunk_documents(
                processed.chunks,
                metadata={
                    "document_id": doc_id,
                    "source_file": file_path,
                    "document_type": processed.document_type,
                    **processed.metadata,
                    **extra_meta,
                },
            )

            if not chunk_objects:
                return IndexResult(
                    document_id=doc_id,
                    source_file=file_path,
                    document_type=processed.document_type,
                    chunk_count=0,
                    collection=target_collection,
                    success=False,
                    error="Chunking produced no output",
                )

            # Step 3: Embed all chunks in batches
            chunk_texts = [c.text for c in chunk_objects]
            _LOGGER.info(
                "Embedding %d chunks from %r", len(chunk_texts), os.path.basename(file_path)
            )
            embedding_result = await self._embedder.embed_batch(chunk_texts)

            # Step 4: Build DocumentRecords
            records: list[DocumentRecord] = []
            for idx, (chunk, vector) in enumerate(
                zip(chunk_objects, embedding_result.vectors)
            ):
                chunk_id = f"{doc_id}_chunk_{idx:04d}"
                record_meta = {
                    "chunk_index": idx,
                    "total_chunks": len(chunk_objects),
                    **chunk.metadata,
                }
                records.append(
                    DocumentRecord(
                        id=chunk_id,
                        text=chunk.text,
                        vector=vector,
                        metadata=record_meta,
                        collection=target_collection,
                    )
                )

            # Ensure collection exists with correct dimension
            await self._db.create_collection(
                name=target_collection,
                dimension=self._embedder.dimension,
                distance="cosine",
            )

            # Step 5: Upsert into vector DB
            await self._db.upsert(records)
            _LOGGER.info(
                "Indexed %r: %d chunks into collection %r",
                os.path.basename(file_path), len(records), target_collection,
            )

            return IndexResult(
                document_id=doc_id,
                source_file=file_path,
                document_type=processed.document_type,
                chunk_count=len(records),
                collection=target_collection,
                metadata=processed.metadata,
                success=True,
            )

        except Exception as exc:
            _LOGGER.error("Failed to index document %r: %s", file_path, exc)
            return IndexResult(
                document_id=doc_id,
                source_file=file_path,
                document_type=ext,
                chunk_count=0,
                collection=target_collection,
                success=False,
                error=str(exc),
            )

    async def search(
        self,
        query: str,
        collection: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> SearchResponse:
        """Search for relevant documents.

        Args:
            query: Natural language search query.
            collection: Collection to search (uses default if None).
            top_k: Number of results to return.
            score_threshold: Minimum similarity score.
            filter_metadata: Optional metadata filter.

        Returns:
            SearchResponse with ranked results and context.
        """
        if not self._initialized:
            await self.initialize()

        target_collection = collection or self._default_collection
        return await self._searcher.search(
            query=query,
            collection=target_collection,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_metadata=filter_metadata,
        )

    async def reason(
        self,
        query: str,
        collection: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> ReasonResult:
        """Answer a question by searching and reasoning over the results.

        Full pipeline: query → search → build context → LLM reasoning.

        Args:
            query: The user's question.
            collection: Collection to search.
            top_k: Number of context documents.
            score_threshold: Minimum search score.

        Returns:
            ReasonResult with the LLM answer and source attribution.
        """
        if not self._initialized:
            await self.initialize()

        # Search for relevant context
        search_response = await self.search(
            query=query,
            collection=collection,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        context = search_response.context_text
        if not context:
            context = "No relevant documents found in the knowledge base."

        # LLM reasoning over context
        try:
            llm_response: LLMResponse = await self._llm.reason(
                query=query, context=context
            )
        except Exception as exc:
            _LOGGER.error("LLM reasoning failed: %s", exc)
            raise

        return ReasonResult(
            answer=llm_response.content,
            query=query,
            sources=search_response.sources,
            model=llm_response.model,
            provider=llm_response.provider,
            search_results_count=len(search_response.results),
            usage=llm_response.usage,
        )

    async def list_collections(self) -> list[str]:
        """List all vector DB collections.

        Returns:
            List of collection name strings.
        """
        return await self._db.list_collections()

    async def list_documents(self, collection: str | None = None) -> list[dict]:
        """List all unique documents in a collection.

        Args:
            collection: Collection name (uses default if None).

        Returns:
            List of dicts with document_id, source_file, document_type, chunk_count.
        """
        target_collection = collection or self._default_collection
        return await self._db.list_documents(target_collection)

    async def delete_document(
        self, document_id: str, collection: str | None = None
    ) -> bool:
        """Delete all chunks of a document from the vector DB.

        Args:
            document_id: The logical document ID (from IndexResult.document_id).
            collection: Collection containing the document.

        Returns:
            True if successful, False if an error occurred.
        """
        target_collection = collection or self._default_collection
        try:
            await self._db.delete(
                collection=target_collection, document_id=document_id
            )
            _LOGGER.info(
                "Deleted document %r from collection %r", document_id, target_collection
            )
            return True
        except Exception as exc:
            _LOGGER.error("Failed to delete document %r: %s", document_id, exc)
            return False

    async def health_check(self) -> dict[str, bool]:
        """Check health of all subsystems.

        Returns:
            Dict mapping subsystem name to health status.
        """
        results = {}
        for name, component in [
            ("llm", self._llm),
            ("embedder", self._embedder),
            ("vector_db", self._db),
        ]:
            try:
                results[name] = await component.health_check()
            except Exception as exc:
                _LOGGER.warning("%s health check threw: %s", name, exc)
                results[name] = False
        return results

    @staticmethod
    def _generate_document_id(file_path: str) -> str:
        """Generate a stable, unique document ID from the file path.

        Uses a SHA-256 hash of the normalized absolute path so the
        same file always gets the same ID, enabling idempotent re-indexing.

        Args:
            file_path: Absolute file path.

        Returns:
            Hex string document ID (16 chars).
        """
        normalized = os.path.abspath(file_path)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
