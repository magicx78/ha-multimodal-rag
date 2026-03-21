"""Service definitions and handlers for Multimodal RAG."""
from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse

from .const import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_TOP_K,
    DOMAIN,
    SERVICE_DELETE_DOCUMENT,
    SERVICE_LIST_COLLECTIONS,
    SERVICE_REASON,
    SERVICE_SEARCH,
    SERVICE_UPLOAD_DOCUMENT,
)

_LOGGER = logging.getLogger(__name__)

# ── Service schemas ──────────────────────────────────────────────────────────

SCHEMA_UPLOAD_DOCUMENT = vol.Schema(
    {
        vol.Required("file_path"): str,
        vol.Optional("collection", default=DEFAULT_COLLECTION_NAME): str,
        vol.Optional("metadata", default={}): dict,
    }
)

SCHEMA_SEARCH = vol.Schema(
    {
        vol.Required("query"): str,
        vol.Optional("collection", default=DEFAULT_COLLECTION_NAME): str,
        vol.Optional("top_k", default=DEFAULT_TOP_K): vol.All(int, vol.Range(min=1, max=50)),
        vol.Optional("score_threshold", default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
        ),
    }
)

SCHEMA_REASON = vol.Schema(
    {
        vol.Required("query"): str,
        vol.Optional("collection", default=DEFAULT_COLLECTION_NAME): str,
        vol.Optional("top_k", default=DEFAULT_TOP_K): vol.All(int, vol.Range(min=1, max=20)),
        vol.Optional("score_threshold", default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
        ),
    }
)

SCHEMA_LIST_COLLECTIONS = vol.Schema({})

SCHEMA_DELETE_DOCUMENT = vol.Schema(
    {
        vol.Required("document_id"): str,
        vol.Optional("collection", default=DEFAULT_COLLECTION_NAME): str,
    }
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register all Multimodal RAG services with Home Assistant.

    Called from async_setup_entry in __init__.py. Each service
    handler pulls the RAGEngine from hass.data[DOMAIN].

    Args:
        hass: Home Assistant instance.
    """
    from .rag.engine import RAGEngine  # noqa: PLC0415

    def _get_engine() -> RAGEngine:
        """Retrieve the RAG engine from hass.data."""
        engine = hass.data.get(DOMAIN, {}).get("engine")
        if engine is None:
            raise RuntimeError(
                "Multimodal RAG engine is not initialized. "
                "Check that the integration is properly configured."
            )
        return engine

    # ── upload_document ──────────────────────────────────────────────────────
    async def handle_upload_document(call: ServiceCall) -> ServiceResponse:
        """Handle multimodal_rag.upload_document service call.

        Accepts a file path, processes the document through the full
        indexing pipeline (process → chunk → embed → store), and
        returns the indexing result as a response dict.
        """
        engine = _get_engine()
        file_path: str = call.data["file_path"]
        collection: str = call.data.get("collection", DEFAULT_COLLECTION_NAME)
        metadata: dict = call.data.get("metadata", {})

        if not os.path.exists(file_path):
            _LOGGER.error("upload_document: file not found: %r", file_path)
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "document_id": None,
            }

        _LOGGER.info("upload_document: indexing %r into collection %r", file_path, collection)

        try:
            result = await engine.index_document(
                file_path=file_path,
                collection=collection,
                metadata=metadata,
            )
        except Exception as exc:
            _LOGGER.error("upload_document failed: %s", exc)
            return {"success": False, "error": str(exc), "document_id": None}

        # Fire HA event
        hass.bus.async_fire(
            f"{DOMAIN}_document_indexed",
            {
                "document_id": result.document_id,
                "source_file": result.source_file,
                "document_type": result.document_type,
                "chunk_count": result.chunk_count,
                "collection": result.collection,
                "success": result.success,
            },
        )

        return {
            "success": result.success,
            "document_id": result.document_id,
            "source_file": result.source_file,
            "document_type": result.document_type,
            "chunk_count": result.chunk_count,
            "collection": result.collection,
            "error": result.error,
        }

    # ── search ───────────────────────────────────────────────────────────────
    async def handle_search(call: ServiceCall) -> ServiceResponse:
        """Handle multimodal_rag.search service call.

        Embeds the query and retrieves the most similar document chunks.
        Returns a list of results with scores, source attribution, and
        the formatted context string.
        """
        engine = _get_engine()
        query: str = call.data["query"]
        collection: str = call.data.get("collection", DEFAULT_COLLECTION_NAME)
        top_k: int = call.data.get("top_k", DEFAULT_TOP_K)
        score_threshold: float = call.data.get("score_threshold", 0.0)

        _LOGGER.info("search: query=%r collection=%r top_k=%d", query[:80], collection, top_k)

        try:
            response = await engine.search(
                query=query,
                collection=collection,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            _LOGGER.error("search failed: %s", exc)
            return {"success": False, "error": str(exc), "results": []}

        results_data = [
            {
                "id": r.id,
                "text": r.text[:500] + ("..." if len(r.text) > 500 else ""),
                "score": round(r.score, 4),
                "source_file": r.source_file,
                "metadata": r.metadata,
            }
            for r in response.results
        ]

        hass.bus.async_fire(
            f"{DOMAIN}_search_completed",
            {"query": query, "result_count": len(results_data), "collection": collection},
        )

        return {
            "success": True,
            "query": query,
            "collection": collection,
            "result_count": len(results_data),
            "results": results_data,
            "sources": response.sources,
        }

    # ── reason ───────────────────────────────────────────────────────────────
    async def handle_reason(call: ServiceCall) -> ServiceResponse:
        """Handle multimodal_rag.reason service call.

        Searches for relevant context, then asks the LLM to answer
        the question based on those documents. Returns the answer,
        sources, and token usage.
        """
        engine = _get_engine()
        query: str = call.data["query"]
        collection: str = call.data.get("collection", DEFAULT_COLLECTION_NAME)
        top_k: int = call.data.get("top_k", DEFAULT_TOP_K)
        score_threshold: float = call.data.get("score_threshold", 0.0)

        _LOGGER.info("reason: query=%r collection=%r", query[:80], collection)

        try:
            result = await engine.reason(
                query=query,
                collection=collection,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            _LOGGER.error("reason failed: %s", exc)
            return {"success": False, "error": str(exc), "answer": ""}

        return {
            "success": True,
            "answer": result.answer,
            "query": result.query,
            "sources": result.sources,
            "model": result.model,
            "provider": result.provider,
            "search_results_count": result.search_results_count,
            "usage": result.usage,
        }

    # ── list_collections ─────────────────────────────────────────────────────
    async def handle_list_collections(call: ServiceCall) -> ServiceResponse:
        """Handle multimodal_rag.list_collections service call.

        Returns a list of all collection names in the vector database.
        """
        engine = _get_engine()
        try:
            collections = await engine.list_collections()
        except Exception as exc:
            _LOGGER.error("list_collections failed: %s", exc)
            return {"success": False, "error": str(exc), "collections": []}

        return {"success": True, "collections": collections, "count": len(collections)}

    # ── delete_document ──────────────────────────────────────────────────────
    async def handle_delete_document(call: ServiceCall) -> ServiceResponse:
        """Handle multimodal_rag.delete_document service call.

        Removes a document and all its chunks from the vector database.
        """
        engine = _get_engine()
        document_id: str = call.data["document_id"]
        collection: str = call.data.get("collection", DEFAULT_COLLECTION_NAME)

        _LOGGER.info("delete_document: id=%r collection=%r", document_id, collection)

        try:
            success = await engine.delete_document(
                document_id=document_id, collection=collection
            )
        except Exception as exc:
            _LOGGER.error("delete_document failed: %s", exc)
            return {"success": False, "error": str(exc)}

        return {
            "success": success,
            "document_id": document_id,
            "collection": collection,
        }

    # ── Register all services ────────────────────────────────────────────────
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPLOAD_DOCUMENT,
        handle_upload_document,
        schema=SCHEMA_UPLOAD_DOCUMENT,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH,
        handle_search,
        schema=SCHEMA_SEARCH,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REASON,
        handle_reason,
        schema=SCHEMA_REASON,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_COLLECTIONS,
        handle_list_collections,
        schema=SCHEMA_LIST_COLLECTIONS,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_DOCUMENT,
        handle_delete_document,
        schema=SCHEMA_DELETE_DOCUMENT,
        supports_response=SupportsResponse.ONLY,
    )

    _LOGGER.info("Registered %d Multimodal RAG services", 5)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove all registered Multimodal RAG services.

    Called during async_unload_entry cleanup.

    Args:
        hass: Home Assistant instance.
    """
    for service in [
        SERVICE_UPLOAD_DOCUMENT,
        SERVICE_SEARCH,
        SERVICE_REASON,
        SERVICE_LIST_COLLECTIONS,
        SERVICE_DELETE_DOCUMENT,
    ]:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    _LOGGER.info("Unregistered Multimodal RAG services")
