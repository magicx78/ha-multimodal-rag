"""SQLite vector database provider (fallback implementation)."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import sqlite3
from typing import Any

from .base import DocumentRecord, SearchResult, VectorDBProvider
from .factory import VectorDBFactory

_LOGGER = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class SQLiteVectorProvider(VectorDBProvider):
    """Fallback vector database using SQLite with JSON-stored vectors.

    Not suitable for large-scale production use (O(n) scan), but
    works without any external dependencies. Ideal for development,
    testing, or very small document sets (<10k chunks).
    """

    def __init__(self, db_path: str = "/config/multimodal_rag/vectors.db", **kwargs: Any) -> None:
        """Initialize the SQLite provider.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Create a SQLite connection with WAL mode enabled."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _table_name(self, collection: str) -> str:
        """Return sanitized table name for a collection."""
        safe = "".join(c if c.isalnum() or c == "_" else "_" for c in collection)
        return f"vec_{safe}"

    def _ensure_table(self, conn: sqlite3.Connection, collection: str) -> None:
        """Create the collection table if it doesn't exist."""
        table = self._table_name(collection)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                vector TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{{}}'
            )
        """)
        conn.commit()

    async def create_collection(
        self, name: str, dimension: int, distance: str = "cosine"
    ) -> None:
        """Create a SQLite table for this collection."""
        loop = asyncio.get_event_loop()

        def _create():
            with self._get_connection() as conn:
                self._ensure_table(conn, name)

        await loop.run_in_executor(None, _create)
        _LOGGER.info("Created SQLite collection %r", name)

    async def delete_collection(self, name: str) -> None:
        """Drop the SQLite table for this collection."""
        loop = asyncio.get_event_loop()

        def _drop():
            table = self._table_name(name)
            with self._get_connection() as conn:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
                conn.commit()

        await loop.run_in_executor(None, _drop)
        _LOGGER.info("Deleted SQLite collection %r", name)

    async def list_collections(self) -> list[str]:
        """Return all collection names from SQLite tables."""
        loop = asyncio.get_event_loop()

        def _list():
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_%'"
                )
                return [row["name"][4:] for row in cursor.fetchall()]

        return await loop.run_in_executor(None, _list)

    async def upsert(self, records: list[DocumentRecord]) -> None:
        """Insert or replace document records.

        Args:
            records: Records to upsert.
        """
        loop = asyncio.get_event_loop()

        def _upsert():
            with self._get_connection() as conn:
                for record in records:
                    self._ensure_table(conn, record.collection)
                    table = self._table_name(record.collection)
                    conn.execute(
                        f"INSERT OR REPLACE INTO {table} (id, text, vector, metadata) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            record.id,
                            record.text,
                            json.dumps(record.vector),
                            json.dumps(record.metadata),
                        ),
                    )
                conn.commit()

        await loop.run_in_executor(None, _upsert)
        _LOGGER.debug("Upserted %d records into SQLite", len(records))

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Perform linear-scan cosine similarity search.

        Args:
            collection: Collection to search.
            vector: Query vector.
            top_k: Number of results.
            score_threshold: Minimum score.
            filter_metadata: Not supported in SQLite (ignored with warning).

        Returns:
            Top-K most similar records.
        """
        if filter_metadata:
            _LOGGER.warning("SQLite provider does not support metadata filtering")

        loop = asyncio.get_event_loop()

        def _search() -> list[SearchResult]:
            table = self._table_name(collection)
            with self._get_connection() as conn:
                # Check if table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                )
                if not cursor.fetchone():
                    return []

                cursor = conn.execute(f"SELECT id, text, vector, metadata FROM {table}")
                rows = cursor.fetchall()

            scored = []
            for row in rows:
                stored_vector = json.loads(row["vector"])
                score = _cosine_similarity(vector, stored_vector)
                if score >= score_threshold:
                    scored.append((score, row))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, row in scored[:top_k]:
                metadata = json.loads(row["metadata"])
                results.append(
                    SearchResult(
                        id=row["id"],
                        text=row["text"],
                        score=score,
                        metadata=metadata,
                        collection=collection,
                    )
                )
            return results

        return await loop.run_in_executor(None, _search)

    async def delete(self, collection: str, document_id: str) -> None:
        """Delete a document by ID.

        Args:
            collection: Collection name.
            document_id: Document ID.
        """
        loop = asyncio.get_event_loop()

        def _delete():
            table = self._table_name(collection)
            with self._get_connection() as conn:
                conn.execute(f"DELETE FROM {table} WHERE id=?", (document_id,))
                conn.commit()

        await loop.run_in_executor(None, _delete)
        _LOGGER.info("Deleted document %r from SQLite collection %r", document_id, collection)

    async def get(self, collection: str, document_id: str) -> DocumentRecord | None:
        """Retrieve a document by ID.

        Args:
            collection: Collection name.
            document_id: Document ID.

        Returns:
            DocumentRecord or None.
        """
        loop = asyncio.get_event_loop()

        def _get() -> DocumentRecord | None:
            table = self._table_name(collection)
            with self._get_connection() as conn:
                cursor = conn.execute(
                    f"SELECT id, text, vector, metadata FROM {table} WHERE id=?",
                    (document_id,),
                )
                row = cursor.fetchone()
            if not row:
                return None
            return DocumentRecord(
                id=row["id"],
                text=row["text"],
                vector=json.loads(row["vector"]),
                metadata=json.loads(row["metadata"]),
                collection=collection,
            )

        return await loop.run_in_executor(None, _get)

    async def health_check(self) -> bool:
        """Verify SQLite file is accessible."""
        try:
            loop = asyncio.get_event_loop()

            def _check():
                with self._get_connection() as conn:
                    conn.execute("SELECT 1")
                return True

            return await loop.run_in_executor(None, _check)
        except Exception as exc:
            _LOGGER.warning("SQLite health check failed: %s", exc)
            return False


# Auto-register
VectorDBFactory.register("sqlite", SQLiteVectorProvider)
