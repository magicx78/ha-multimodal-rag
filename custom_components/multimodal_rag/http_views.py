"""HTTP REST API views for the Multimodal RAG web panel."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DEFAULT_COLLECTION_NAME, DEFAULT_TOP_K, DOMAIN

_LOGGER = logging.getLogger(__name__)


class _RAGBaseView(HomeAssistantView):
    """Shared helper — pulls the RAG engine from hass.data."""

    requires_auth = True

    def _engine(self, request: web.Request):
        hass: HomeAssistant = request.app["hass"]
        engine = hass.data.get(DOMAIN, {}).get("engine")
        if engine is None:
            raise web.HTTPServiceUnavailable(
                text=json.dumps({"error": "RAG engine not initialised"}),
                content_type="application/json",
            )
        return engine, hass


# ── Collections ──────────────────────────────────────────────────────────────

class CollectionsView(_RAGBaseView):
    """GET /api/multimodal_rag/collections"""

    url = "/api/multimodal_rag/collections"
    name = "api:multimodal_rag:collections"

    async def get(self, request: web.Request) -> web.Response:
        engine, _ = self._engine(request)
        try:
            collections = await engine.list_collections()
            return self.json({"success": True, "collections": collections})
        except Exception as exc:
            _LOGGER.error("list_collections failed: %s", exc)
            return self.json({"success": False, "error": str(exc)}, status_code=500)


# ── Documents (browse) ───────────────────────────────────────────────────────

class DocumentsView(_RAGBaseView):
    """GET /api/multimodal_rag/documents?collection=<name>"""

    url = "/api/multimodal_rag/documents"
    name = "api:multimodal_rag:documents"

    async def get(self, request: web.Request) -> web.Response:
        engine, _ = self._engine(request)
        collection = request.query.get("collection", DEFAULT_COLLECTION_NAME)
        try:
            documents = await engine.list_documents(collection=collection)
            return self.json(
                {"success": True, "collection": collection, "documents": documents}
            )
        except Exception as exc:
            _LOGGER.error("list_documents failed: %s", exc)
            return self.json({"success": False, "error": str(exc)}, status_code=500)


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadView(_RAGBaseView):
    """POST /api/multimodal_rag/upload

    Accepts either:
    - multipart/form-data with field ``file`` (browser file upload)
    - application/json with field ``file_path`` (server-side path)
    """

    url = "/api/multimodal_rag/upload"
    name = "api:multimodal_rag:upload"

    async def post(self, request: web.Request) -> web.Response:  # noqa: PLR0911
        engine, hass = self._engine(request)
        content_type = request.content_type or ""

        if "multipart" in content_type:
            return await self._handle_multipart(request, engine, hass)
        return await self._handle_json(request, engine)

    # ── internal helpers ──────────────────────────────────────────────────

    async def _handle_json(self, request: web.Request, engine) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return self.json({"success": False, "error": "Invalid JSON body"}, status_code=400)

        file_path: str = data.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            return self.json(
                {"success": False, "error": f"File not found: {file_path}"}, status_code=400
            )

        collection = data.get("collection", DEFAULT_COLLECTION_NAME)
        metadata = data.get("metadata", {})
        return await self._index_and_respond(engine, file_path, collection, metadata)

    async def _handle_multipart(
        self, request: web.Request, engine, hass: HomeAssistant
    ) -> web.Response:
        storage_path = hass.data.get(DOMAIN, {}).get(
            "storage_path", hass.config.path("multimodal_rag")
        )
        upload_dir = os.path.join(storage_path, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        collection = DEFAULT_COLLECTION_NAME
        metadata: dict[str, Any] = {}
        saved_path: str | None = None

        try:
            reader = await request.multipart()
            field = await reader.next()
            while field is not None:
                if field.name == "collection":
                    collection = (await field.read()).decode()
                elif field.name == "metadata":
                    try:
                        metadata = json.loads((await field.read()).decode())
                    except Exception:
                        pass
                elif field.name == "file" and field.filename:
                    dest = os.path.join(upload_dir, field.filename)
                    with open(dest, "wb") as fh:
                        while True:
                            chunk = await field.read_chunk(65536)
                            if not chunk:
                                break
                            fh.write(chunk)
                    saved_path = dest
                field = await reader.next()
        except Exception as exc:
            _LOGGER.error("Multipart read error: %s", exc)
            return self.json({"success": False, "error": str(exc)}, status_code=400)

        if saved_path is None:
            return self.json(
                {"success": False, "error": "No file field found in request"}, status_code=400
            )

        return await self._index_and_respond(engine, saved_path, collection, metadata)

    async def _index_and_respond(
        self, engine, file_path: str, collection: str, metadata: dict
    ) -> web.Response:
        try:
            result = await engine.index_document(
                file_path=file_path, collection=collection, metadata=metadata
            )
        except Exception as exc:
            _LOGGER.error("index_document failed: %s", exc)
            return self.json({"success": False, "error": str(exc)}, status_code=500)

        return self.json(
            {
                "success": result.success,
                "document_id": result.document_id,
                "source_file": os.path.basename(result.source_file),
                "document_type": result.document_type,
                "chunk_count": result.chunk_count,
                "collection": result.collection,
                "error": result.error,
            }
        )


# ── Search ────────────────────────────────────────────────────────────────────

class SearchView(_RAGBaseView):
    """POST /api/multimodal_rag/search"""

    url = "/api/multimodal_rag/search"
    name = "api:multimodal_rag:search"

    async def post(self, request: web.Request) -> web.Response:
        engine, _ = self._engine(request)
        try:
            data = await request.json()
        except Exception:
            return self.json({"success": False, "error": "Invalid JSON"}, status_code=400)

        query = (data.get("query") or "").strip()
        if not query:
            return self.json({"success": False, "error": "query is required"}, status_code=400)

        collection = data.get("collection", DEFAULT_COLLECTION_NAME)
        top_k = min(int(data.get("top_k", DEFAULT_TOP_K)), 50)
        score_threshold = float(data.get("score_threshold", 0.0))

        try:
            response = await engine.search(
                query=query,
                collection=collection,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            _LOGGER.error("search failed: %s", exc)
            return self.json({"success": False, "error": str(exc)}, status_code=500)

        results = [
            {
                "id": r.id,
                "text": r.text[:1000] + ("…" if len(r.text) > 1000 else ""),
                "score": round(r.score, 4),
                "source_file": r.source_file,
                "metadata": r.metadata,
            }
            for r in response.results
        ]
        return self.json(
            {
                "success": True,
                "query": query,
                "collection": collection,
                "results": results,
                "sources": response.sources,
            }
        )


# ── Reason ────────────────────────────────────────────────────────────────────

class ReasonView(_RAGBaseView):
    """POST /api/multimodal_rag/reason"""

    url = "/api/multimodal_rag/reason"
    name = "api:multimodal_rag:reason"

    async def post(self, request: web.Request) -> web.Response:
        engine, _ = self._engine(request)
        try:
            data = await request.json()
        except Exception:
            return self.json({"success": False, "error": "Invalid JSON"}, status_code=400)

        query = (data.get("query") or "").strip()
        if not query:
            return self.json({"success": False, "error": "query is required"}, status_code=400)

        collection = data.get("collection", DEFAULT_COLLECTION_NAME)
        top_k = min(int(data.get("top_k", DEFAULT_TOP_K)), 20)
        score_threshold = float(data.get("score_threshold", 0.0))

        try:
            result = await engine.reason(
                query=query,
                collection=collection,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            _LOGGER.error("reason failed: %s", exc)
            return self.json({"success": False, "error": str(exc)}, status_code=500)

        return self.json(
            {
                "success": True,
                "answer": result.answer,
                "query": result.query,
                "sources": result.sources,
                "model": result.model,
                "provider": result.provider,
                "search_results_count": result.search_results_count,
                "usage": result.usage,
            }
        )


# ── Delete document ───────────────────────────────────────────────────────────

class DeleteDocumentView(_RAGBaseView):
    """DELETE /api/multimodal_rag/document/{doc_id}?collection=<name>"""

    url = "/api/multimodal_rag/document/{doc_id}"
    name = "api:multimodal_rag:delete_document"

    async def delete(self, request: web.Request, doc_id: str) -> web.Response:
        engine, _ = self._engine(request)
        collection = request.query.get("collection", DEFAULT_COLLECTION_NAME)
        try:
            success = await engine.delete_document(
                document_id=doc_id, collection=collection
            )
            return self.json(
                {"success": success, "document_id": doc_id, "collection": collection}
            )
        except Exception as exc:
            _LOGGER.error("delete_document failed: %s", exc)
            return self.json({"success": False, "error": str(exc)}, status_code=500)


# ── Registration ──────────────────────────────────────────────────────────────

def async_register_views(hass: HomeAssistant) -> None:
    """Register all Multimodal RAG HTTP views."""
    hass.http.register_view(CollectionsView())
    hass.http.register_view(DocumentsView())
    hass.http.register_view(UploadView())
    hass.http.register_view(SearchView())
    hass.http.register_view(ReasonView())
    hass.http.register_view(DeleteDocumentView())
    _LOGGER.info("Registered Multimodal RAG HTTP views")
