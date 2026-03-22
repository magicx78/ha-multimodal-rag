"""Qdrant vector database provider implementation."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from .base import DocumentRecord, SearchResult, VectorDBProvider
from .factory import VectorDBFactory

_LOGGER = logging.getLogger(__name__)

_DISTANCE_MAP = {
    "cosine": "Cosine",
    "dot": "Dot",
    "euclidean": "Euclid",
}


class QdrantProvider(VectorDBProvider):
    """Vector database backed by Qdrant.

    Qdrant is the primary vector store. Expects a running Qdrant
    instance (Docker recommended). Collections are created on demand.
    Supports batch upsert, filtered search, and collection management.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: str | None = None,
        prefer_grpc: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the Qdrant provider.

        Args:
            host: Qdrant server hostname.
            port: Qdrant REST API port (default 6333).
            api_key: Optional Qdrant Cloud API key.
            prefer_grpc: Use gRPC instead of REST for faster bulk ops.
        """
        self._host = host
        self._port = port
        self._api_key = api_key
        self._prefer_grpc = prefer_grpc
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily create the async Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import AsyncQdrantClient  # noqa: PLC0415
                self._client = AsyncQdrantClient(
                    host=self._host,
                    port=self._port,
                    api_key=self._api_key,
                    prefer_grpc=self._prefer_grpc,
                )
            except ImportError as exc:
                raise ImportError(
                    "qdrant-client package is required. pip install qdrant-client"
                ) from exc
        return self._client

    async def create_collection(
        self, name: str, dimension: int, distance: str = "cosine"
    ) -> None:
        """Create a Qdrant collection if it does not already exist.

        Args:
            name: Collection name.
            dimension: Vector dimension.
            distance: Distance metric name.
        """
        from qdrant_client.models import Distance, VectorParams  # noqa: PLC0415

        client = self._get_client()
        distance_enum = Distance[_DISTANCE_MAP.get(distance, "Cosine").upper()]

        existing = await client.get_collections()
        existing_names = [c.name for c in existing.collections]

        if name not in existing_names:
            await client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimension, distance=distance_enum),
            )
            _LOGGER.info("Created Qdrant collection %r (dim=%d)", name, dimension)
        else:
            _LOGGER.debug("Collection %r already exists", name)

    async def delete_collection(self, name: str) -> None:
        """Delete a Qdrant collection.

        Args:
            name: Collection name.
        """
        client = self._get_client()
        await client.delete_collection(collection_name=name)
        _LOGGER.info("Deleted Qdrant collection %r", name)

    async def list_collections(self) -> list[str]:
        """Return all Qdrant collection names."""
        client = self._get_client()
        response = await client.get_collections()
        return [c.name for c in response.collections]

    async def upsert(self, records: list[DocumentRecord]) -> None:
        """Upsert document records into their respective collections.

        Groups records by collection for efficient bulk upserts.

        Args:
            records: List of DocumentRecord objects.
        """
        from qdrant_client.models import PointStruct  # noqa: PLC0415

        client = self._get_client()

        # Group by collection
        by_collection: dict[str, list[DocumentRecord]] = {}
        for record in records:
            by_collection.setdefault(record.collection, []).append(record)

        for collection, recs in by_collection.items():
            points = [
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, r.id)),
                    vector=r.vector,
                    payload={"text": r.text, "doc_id": r.id, **r.metadata},
                )
                for r in recs
            ]
            await client.upsert(collection_name=collection, points=points)
            _LOGGER.debug("Upserted %d records into collection %r", len(points), collection)

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for the most similar vectors in Qdrant.

        Args:
            collection: Collection to search.
            vector: Query vector.
            top_k: Maximum results.
            score_threshold: Minimum score filter.
            filter_metadata: Key-value metadata filters.

        Returns:
            Sorted list of SearchResult.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue  # noqa: PLC0415

        client = self._get_client()

        query_filter = None
        if filter_metadata:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_metadata.items()
            ]
            query_filter = Filter(must=conditions)

        hits = await client.search(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
        )

        results = []
        for hit in hits:
            payload = hit.payload or {}
            text = payload.pop("text", "")
            doc_id = payload.pop("doc_id", str(hit.id))
            results.append(
                SearchResult(
                    id=doc_id,
                    text=text,
                    score=hit.score,
                    metadata=payload,
                    collection=collection,
                )
            )
        _LOGGER.debug("Search in %r returned %d results", collection, len(results))
        return results

    async def delete(self, collection: str, document_id: str) -> None:
        """Delete a document by ID from Qdrant.

        Args:
            collection: Collection name.
            document_id: Document logical ID.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue  # noqa: PLC0415

        client = self._get_client()
        # Delete by payload field doc_id (the logical ID we store)
        await client.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=document_id))]
            ),
        )
        _LOGGER.info("Deleted document %r from collection %r", document_id, collection)

    async def get(self, collection: str, document_id: str) -> DocumentRecord | None:
        """Retrieve a document by its logical ID.

        Args:
            collection: Collection name.
            document_id: Document ID.

        Returns:
            DocumentRecord or None.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue  # noqa: PLC0415

        client = self._get_client()
        results = await client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=document_id))]
            ),
            limit=1,
            with_payload=True,
            with_vectors=True,
        )
        points, _ = results
        if not points:
            return None

        point = points[0]
        payload = dict(point.payload or {})
        text = payload.pop("text", "")
        payload.pop("doc_id", None)
        return DocumentRecord(
            id=document_id,
            text=text,
            vector=list(point.vector) if point.vector else [],
            metadata=payload,
            collection=collection,
        )

    async def list_documents(self, collection: str) -> list[dict]:
        """Return one summary record per unique document in the collection.

        Scrolls through all Qdrant points and groups by document_id payload field.

        Args:
            collection: Collection name.

        Returns:
            List of dicts with document_id, source_file, document_type, chunk_count.
        """
        client = self._get_client()
        try:
            existing = await client.get_collections()
            if collection not in [c.name for c in existing.collections]:
                return []
        except Exception:
            return []

        docs: dict[str, dict] = {}
        offset = None
        while True:
            results = await client.scroll(
                collection_name=collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points, next_offset = results
            for point in points:
                payload = point.payload or {}
                doc_id = payload.get("document_id") or payload.get("doc_id", "")
                if not doc_id:
                    continue
                if doc_id not in docs:
                    docs[doc_id] = {
                        "document_id": doc_id,
                        "source_file": payload.get("source_file", ""),
                        "document_type": payload.get("document_type", "unknown"),
                        "chunk_count": 0,
                    }
                docs[doc_id]["chunk_count"] += 1
            if next_offset is None:
                break
            offset = next_offset

        return sorted(docs.values(), key=lambda d: d["source_file"])

    async def health_check(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            client = self._get_client()
            await client.get_collections()
            return True
        except Exception as exc:
            _LOGGER.warning("Qdrant health check failed: %s", exc)
            return False


# Auto-register
VectorDBFactory.register("qdrant", QdrantProvider)
