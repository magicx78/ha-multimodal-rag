"""Multimodal RAG — Home Assistant Custom Integration.

Provides retrieval-augmented generation (RAG) services backed by:
- LLM: Claude API (primary) or Ollama (fallback)
- Embeddings: Claude Voyage (primary) or Sentence-Transformers (fallback)
- Vector DB: Qdrant (primary) or SQLite (fallback)

Services:
    multimodal_rag.upload_document  — Index a document
    multimodal_rag.search           — Semantic similarity search
    multimodal_rag.reason           — LLM-reasoned Q&A over documents
    multimodal_rag.list_collections — List vector collections
    multimodal_rag.delete_document  — Remove a document
"""
from __future__ import annotations

import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_COLLECTION_NAME,
    CONF_EMBEDDING_API_KEY,
    CONF_EMBEDDING_MODEL,
    CONF_EMBEDDING_PROVIDER,
    CONF_LLM_API_KEY,
    CONF_LLM_BASE_URL,
    CONF_LLM_MODEL,
    CONF_LLM_PROVIDER,
    CONF_STORAGE_PATH,
    CONF_VECTOR_DB_API_KEY,
    CONF_VECTOR_DB_HOST,
    CONF_VECTOR_DB_PORT,
    CONF_VECTOR_DB_PROVIDER,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_EMBEDDING_MODEL_CLAUDE,
    DEFAULT_EMBEDDING_MODEL_ST,
    DEFAULT_LLM_MODEL_CLAUDE,
    DEFAULT_LLM_MODEL_OLLAMA,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_STORAGE_PATH,
    DEFAULT_VECTOR_DB_HOST,
    DEFAULT_VECTOR_DB_PORT,
    DOMAIN,
    EMBEDDING_PROVIDER_CLAUDE,
    LLM_PROVIDER_CLAUDE,
    LLM_PROVIDER_OLLAMA,
    VECTOR_DB_PROVIDER_QDRANT,
    VECTOR_DB_PROVIDER_SQLITE,
)
from .http_views import async_register_views
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Multimodal RAG component (YAML config entry point).

    This integration is configured exclusively via the UI config flow.
    This function just ensures the domain namespace exists.

    Args:
        hass: Home Assistant instance.
        config: YAML configuration dict (unused).

    Returns:
        Always True — setup deferred to config entries.
    """
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Multimodal RAG component setup complete (awaiting config entry)")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multimodal RAG from a config entry.

    Initializes all provider instances (LLM, embeddings, vector DB)
    and the RAG engine, then registers HA services.

    Args:
        hass: Home Assistant instance.
        entry: Config entry with user-provided configuration.

    Returns:
        True if setup succeeded, raises ConfigEntryNotReady otherwise.
    """
    hass.data.setdefault(DOMAIN, {})
    config = entry.data

    _LOGGER.info(
        "Setting up Multimodal RAG (llm=%s, embed=%s, db=%s)",
        config.get(CONF_LLM_PROVIDER),
        config.get(CONF_EMBEDDING_PROVIDER),
        config.get(CONF_VECTOR_DB_PROVIDER),
    )

    try:
        # ── Import all provider modules (auto-registers via module-level code) ──
        from .llm import claude as _  # noqa: F401,PLC0415
        from .llm import ollama as _  # noqa: F401,PLC0415
        from .embeddings import claude_embeddings as _  # noqa: F401,PLC0415
        from .embeddings import sentence_transformers as _  # noqa: F401,PLC0415
        from .db import qdrant_db as _  # noqa: F401,PLC0415
        from .db import sqlite_db as _  # noqa: F401,PLC0415

        # ── Also import processors to register them ──
        from .processors import text_processor as _  # noqa: F401,PLC0415
        from .processors import pdf_processor as _  # noqa: F401,PLC0415
        from .processors import image_processor as _  # noqa: F401,PLC0415
        from .processors import audio_processor as _  # noqa: F401,PLC0415

        # ── Build LLM provider ───────────────────────────────────────────────
        from .llm.factory import LLMFactory  # noqa: PLC0415

        llm_provider_name = config.get(CONF_LLM_PROVIDER, LLM_PROVIDER_CLAUDE)
        if llm_provider_name == LLM_PROVIDER_CLAUDE:
            llm_provider = LLMFactory.create(
                "claude",
                model=config.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL_CLAUDE),
                api_key=config.get(CONF_LLM_API_KEY, ""),
            )
        else:
            llm_provider = LLMFactory.create(
                "ollama",
                model=config.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL_OLLAMA),
                base_url=config.get(CONF_LLM_BASE_URL, DEFAULT_OLLAMA_BASE_URL),
            )

        # ── Build embedding provider ─────────────────────────────────────────
        from .embeddings.factory import EmbeddingFactory  # noqa: PLC0415

        embed_provider_name = config.get(CONF_EMBEDDING_PROVIDER, EMBEDDING_PROVIDER_CLAUDE)
        if embed_provider_name == EMBEDDING_PROVIDER_CLAUDE:
            # Reuse LLM API key if embedding key not separately set
            embed_api_key = (
                config.get(CONF_EMBEDDING_API_KEY)
                or config.get(CONF_LLM_API_KEY, "")
            )
            embedding_provider = EmbeddingFactory.create(
                "claude",
                model=config.get(CONF_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_CLAUDE),
                api_key=embed_api_key,
            )
        else:
            embedding_provider = EmbeddingFactory.create(
                "sentence_transformers",
                model=config.get(CONF_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_ST),
            )

        # ── Build vector DB provider ─────────────────────────────────────────
        from .db.factory import VectorDBFactory  # noqa: PLC0415

        db_provider_name = config.get(CONF_VECTOR_DB_PROVIDER, VECTOR_DB_PROVIDER_QDRANT)
        storage_path = hass.config.path(config.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH))

        if db_provider_name == VECTOR_DB_PROVIDER_QDRANT:
            vector_db = VectorDBFactory.create(
                "qdrant",
                host=config.get(CONF_VECTOR_DB_HOST, DEFAULT_VECTOR_DB_HOST),
                port=config.get(CONF_VECTOR_DB_PORT, DEFAULT_VECTOR_DB_PORT),
                api_key=config.get(CONF_VECTOR_DB_API_KEY) or None,
            )
        else:
            db_path = os.path.join(storage_path, "vectors.db")
            vector_db = VectorDBFactory.create("sqlite", db_path=db_path)

        # ── Assemble the RAG engine ──────────────────────────────────────────
        from .rag.engine import RAGEngine  # noqa: PLC0415

        engine = RAGEngine(
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,
            vector_db=vector_db,
            default_collection=config.get(CONF_COLLECTION_NAME, DEFAULT_COLLECTION_NAME),
            storage_path=storage_path,
        )

        # Initialize (creates collections, storage dirs, etc.)
        await engine.initialize()

        # Store engine in hass.data for service handlers
        hass.data[DOMAIN] = {
            "engine": engine,
            "config_entry_id": entry.entry_id,
            "llm_provider": llm_provider,
            "embedding_provider": embedding_provider,
            "vector_db": vector_db,
            "storage_path": storage_path,
        }

        # Register HA services
        async_register_services(hass)

        # Register HTTP REST API views and the web panel
        async_register_views(hass)
        await _async_register_panel(hass)

        # Register update listener for options flow changes
        entry.async_on_unload(entry.add_update_listener(_async_update_listener))

        _LOGGER.info("Multimodal RAG integration setup complete")
        return True

    except Exception as exc:
        _LOGGER.error("Failed to set up Multimodal RAG: %s", exc, exc_info=True)
        raise ConfigEntryNotReady(
            f"Multimodal RAG setup failed: {exc}"
        ) from exc


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the static www/ path and the sidebar panel (idempotent).

    The panel is an iframe that loads the self-contained panel.html served
    directly from the integration's www/ directory.
    """
    import pathlib  # noqa: PLC0415

    www_path = pathlib.Path(__file__).parent / "www"

    # Serve static files at /multimodal_rag_panel/
    hass.http.register_static_path(
        "/multimodal_rag_panel",
        str(www_path),
        cache_headers=False,
    )

    # Add sidebar panel (only once — skip if already registered)
    try:
        from homeassistant.components.frontend import (  # noqa: PLC0415
            async_register_built_in_panel,
        )

        async_register_built_in_panel(
            hass,
            component_name="iframe",
            sidebar_title="Multimodal RAG",
            sidebar_icon="mdi:brain",
            frontend_url_path="multimodal-rag",
            config={"url": "/multimodal_rag_panel/panel.html"},
            require_admin=True,
        )
        _LOGGER.info("Multimodal RAG web panel registered at /multimodal_rag_panel/panel.html")
    except Exception as exc:
        _LOGGER.warning("Could not register sidebar panel: %s", exc)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Multimodal RAG config entry.

    Removes registered services and clears hass.data.

    Args:
        hass: Home Assistant instance.
        entry: Config entry being unloaded.

    Returns:
        True if unloaded cleanly.
    """
    _LOGGER.info("Unloading Multimodal RAG integration")

    async_unregister_services(hass)

    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options flow updates by reloading the integration.

    Called when the user changes settings via the options flow.

    Args:
        hass: Home Assistant instance.
        entry: Updated config entry.
    """
    _LOGGER.info("Multimodal RAG options updated — reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)
