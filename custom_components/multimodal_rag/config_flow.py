"""Config flow for Multimodal RAG integration."""
from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CLAUDE_ACCESS_API_KEY,
    CLAUDE_ACCESS_NONE,
    CLAUDE_ACCESS_SUBSCRIPTION,
    CLAUDE_ACCESS_TYPES,
    CONF_CLAUDE_ACCESS_TYPE,
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
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_LLM_MODEL_CLAUDE,
    DEFAULT_LLM_MODEL_OLLAMA,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_STORAGE_PATH,
    DEFAULT_VECTOR_DB_HOST,
    DEFAULT_VECTOR_DB_PORT,
    DEFAULT_VECTOR_DB_PROVIDER,
    DOMAIN,
    EMBEDDING_PROVIDER_CLAUDE,
    EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS,
    LLM_PROVIDER_CLAUDE,
    LLM_PROVIDER_OLLAMA,
    VECTOR_DB_PROVIDER_QDRANT,
    VECTOR_DB_PROVIDER_SQLITE,
)

_LOGGER = logging.getLogger(__name__)


class MultimodalRAGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Multi-step config flow for Multimodal RAG.

    Step 0: Claude access type selection
    Step 1: LLM provider choice and credentials
    Step 2: Embedding provider choice
    Step 3: Vector DB configuration
    Step 4: Storage path
    Step 5: Validate and save
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow with an empty user config dict."""
        self._config: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 0: Claude access type selection."""
        # Prevent duplicate entries
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            self._config.update(user_input)
            claude_access = user_input.get(CONF_CLAUDE_ACCESS_TYPE)

            if claude_access == CLAUDE_ACCESS_NONE:
                # Skip Claude, go directly to LLM choice (Ollama only)
                self._config[CONF_LLM_PROVIDER] = LLM_PROVIDER_OLLAMA
                return await self.async_step_embedding_provider()
            else:
                # Has Claude access, configure LLM with Claude
                return await self.async_step_llm_config()

        # Show Claude access type selection
        schema = vol.Schema(
            {
                vol.Required(CONF_CLAUDE_ACCESS_TYPE, default=CLAUDE_ACCESS_API_KEY): vol.In(
                    CLAUDE_ACCESS_TYPES
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "claude_url": "https://console.anthropic.com",
            },
        )

    async def async_step_llm_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: LLM configuration with Claude API Key."""
        errors: dict[str, str] = {}
        claude_access = self._config.get(CONF_CLAUDE_ACCESS_TYPE)

        if user_input is not None:
            self._config.update(user_input)
            self._config[CONF_LLM_PROVIDER] = LLM_PROVIDER_CLAUDE
            return await self.async_step_embedding_provider()

        # Show API Key input based on access type
        access_label = "API Key" if claude_access == CLAUDE_ACCESS_API_KEY else "Subscription Access"

        schema = vol.Schema(
            {
                vol.Required(CONF_LLM_API_KEY, default=""): str,
                vol.Optional(
                    CONF_LLM_MODEL, default=DEFAULT_LLM_MODEL_CLAUDE
                ): str,
            }
        )

        return self.async_show_form(
            step_id="llm_config",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "claude_url": "https://console.anthropic.com",
                "access_type": access_label,
            },
        )

    async def async_step_embedding_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Embedding provider selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config.update(user_input)
            return await self.async_step_vector_db()

        # Suggest matching embedding provider to LLM choice
        llm_provider = self._config.get(CONF_LLM_PROVIDER, DEFAULT_LLM_PROVIDER)
        default_embed = (
            EMBEDDING_PROVIDER_CLAUDE
            if llm_provider == LLM_PROVIDER_CLAUDE
            else EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS
        )
        default_embed_model = (
            DEFAULT_EMBEDDING_MODEL_CLAUDE
            if default_embed == EMBEDDING_PROVIDER_CLAUDE
            else DEFAULT_EMBEDDING_MODEL_ST
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_EMBEDDING_PROVIDER, default=default_embed): vol.In(
                    [EMBEDDING_PROVIDER_CLAUDE, EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS]
                ),
                vol.Optional(CONF_EMBEDDING_MODEL, default=default_embed_model): str,
                vol.Optional(CONF_EMBEDDING_API_KEY, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="embedding_provider",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_vector_db(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: Vector DB configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config.update(user_input)
            return await self.async_step_storage()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_VECTOR_DB_PROVIDER, default=DEFAULT_VECTOR_DB_PROVIDER
                ): vol.In([VECTOR_DB_PROVIDER_QDRANT, VECTOR_DB_PROVIDER_SQLITE]),
                vol.Optional(CONF_VECTOR_DB_HOST, default=DEFAULT_VECTOR_DB_HOST): str,
                vol.Optional(
                    CONF_VECTOR_DB_PORT, default=DEFAULT_VECTOR_DB_PORT
                ): vol.All(int, vol.Range(min=1, max=65535)),
                vol.Optional(CONF_VECTOR_DB_API_KEY, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="vector_db",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_storage(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 4: Storage path configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            storage_path = user_input.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH)
            # Validate that we can create/access the path
            try:
                # Resolve relative paths using Home Assistant config directory
                abs_storage_path = self.hass.config.path(storage_path)
                os.makedirs(abs_storage_path, exist_ok=True)
                test_file = os.path.join(abs_storage_path, ".ha_rag_write_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except OSError as exc:
                _LOGGER.error("Storage path validation failed: %s", exc)
                errors[CONF_STORAGE_PATH] = "invalid_path"
            else:
                self._config.update(user_input)
                return await self.async_step_validate()

        schema = vol.Schema(
            {
                vol.Required(CONF_STORAGE_PATH, default=DEFAULT_STORAGE_PATH): str,
                vol.Optional(
                    CONF_COLLECTION_NAME, default=DEFAULT_COLLECTION_NAME
                ): str,
            }
        )

        return self.async_show_form(
            step_id="storage",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_validate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 5: Validate all connections and create the entry."""
        errors: dict[str, str] = {}

        validation_ok = await self._validate_config(errors)

        if validation_ok:
            return self.async_create_entry(
                title="Multimodal RAG",
                data=self._config,
            )

        # Show errors and let user go back (restart flow)
        return self.async_show_form(
            step_id="validate",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "error_details": "; ".join(errors.values())
            },
        )

    async def _validate_config(self, errors: dict[str, str]) -> bool:
        """Validate all configured providers can connect.

        Args:
            errors: Error dict to populate with validation failures.

        Returns:
            True if all validations pass.
        """
        config = self._config
        all_ok = True

        # Validate LLM provider
        llm_provider = config.get(CONF_LLM_PROVIDER)
        try:
            if llm_provider == LLM_PROVIDER_CLAUDE:
                from .llm.claude import ClaudeProvider  # noqa: PLC0415
                provider = ClaudeProvider(
                    model=config.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL_CLAUDE),
                    api_key=config.get(CONF_LLM_API_KEY, ""),
                )
            else:
                from .llm.ollama import OllamaProvider  # noqa: PLC0415
                provider = OllamaProvider(
                    model=config.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL_OLLAMA),
                    base_url=config.get(CONF_LLM_BASE_URL, DEFAULT_OLLAMA_BASE_URL),
                )
            if not await provider.health_check():
                errors["llm"] = "llm_connection_failed"
                all_ok = False
        except Exception as exc:
            _LOGGER.error("LLM validation error: %s", exc)
            errors["llm"] = "llm_connection_failed"
            all_ok = False

        # Validate embedding provider
        embed_provider = config.get(CONF_EMBEDDING_PROVIDER)
        try:
            if embed_provider == EMBEDDING_PROVIDER_CLAUDE:
                from .embeddings.claude_embeddings import ClaudeEmbeddingProvider  # noqa: PLC0415
                embedder = ClaudeEmbeddingProvider(
                    model=config.get(CONF_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_CLAUDE),
                    api_key=config.get(CONF_EMBEDDING_API_KEY, "") or config.get(CONF_LLM_API_KEY, ""),
                )
            else:
                from .embeddings.sentence_transformers import SentenceTransformerProvider  # noqa: PLC0415
                embedder = SentenceTransformerProvider(
                    model=config.get(CONF_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_ST),
                )
            if not await embedder.health_check():
                errors["embedding"] = "embedding_connection_failed"
                all_ok = False
        except Exception as exc:
            _LOGGER.error("Embedding validation error: %s", exc)
            errors["embedding"] = "embedding_connection_failed"
            all_ok = False

        # Validate vector DB
        db_provider = config.get(CONF_VECTOR_DB_PROVIDER)
        try:
            if db_provider == VECTOR_DB_PROVIDER_QDRANT:
                from .db.qdrant_db import QdrantProvider  # noqa: PLC0415
                db = QdrantProvider(
                    host=config.get(CONF_VECTOR_DB_HOST, DEFAULT_VECTOR_DB_HOST),
                    port=config.get(CONF_VECTOR_DB_PORT, DEFAULT_VECTOR_DB_PORT),
                    api_key=config.get(CONF_VECTOR_DB_API_KEY) or None,
                )
            else:
                from .db.sqlite_db import SQLiteVectorProvider  # noqa: PLC0415
                db_path = os.path.join(
                    config.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH), "vectors.db"
                )
                db = SQLiteVectorProvider(db_path=db_path)
            if not await db.health_check():
                errors["vector_db"] = "vector_db_connection_failed"
                all_ok = False
        except Exception as exc:
            _LOGGER.error("Vector DB validation error: %s", exc)
            errors["vector_db"] = "vector_db_connection_failed"
            all_ok = False

        return all_ok

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MultimodalRAGOptionsFlow:
        """Return the options flow handler."""
        return MultimodalRAGOptionsFlow(config_entry)


class MultimodalRAGOptionsFlow(config_entries.OptionsFlow):
    """Options flow for updating Multimodal RAG settings post-setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options update."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.data
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LLM_MODEL,
                    default=current.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL_CLAUDE),
                ): str,
                vol.Optional(
                    CONF_EMBEDDING_MODEL,
                    default=current.get(CONF_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_CLAUDE),
                ): str,
                vol.Optional(
                    CONF_STORAGE_PATH,
                    default=current.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH),
                ): str,
                vol.Optional(
                    CONF_COLLECTION_NAME,
                    default=current.get(CONF_COLLECTION_NAME, DEFAULT_COLLECTION_NAME),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
