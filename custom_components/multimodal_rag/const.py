"""Constants for the Multimodal RAG integration."""
from __future__ import annotations

from typing import Final

# Integration domain
DOMAIN: Final = "multimodal_rag"
VERSION: Final = "1.0.0"
ATTRIBUTION: Final = "Data provided by Multimodal RAG"

# Configuration keys
CONF_LLM_PROVIDER: Final = "llm_provider"
CONF_LLM_MODEL: Final = "llm_model"
CONF_LLM_API_KEY: Final = "llm_api_key"
CONF_LLM_BASE_URL: Final = "llm_base_url"
CONF_CLAUDE_ACCESS_TYPE: Final = "claude_access_type"
CONF_EMBEDDING_PROVIDER: Final = "embedding_provider"
CONF_EMBEDDING_MODEL: Final = "embedding_model"
CONF_EMBEDDING_API_KEY: Final = "embedding_api_key"
CONF_VECTOR_DB_PROVIDER: Final = "vector_db_provider"
CONF_VECTOR_DB_HOST: Final = "vector_db_host"
CONF_VECTOR_DB_PORT: Final = "vector_db_port"
CONF_VECTOR_DB_API_KEY: Final = "vector_db_api_key"
CONF_STORAGE_PATH: Final = "storage_path"
CONF_COLLECTION_NAME: Final = "collection_name"

# Provider names
LLM_PROVIDER_CLAUDE: Final = "claude"
LLM_PROVIDER_OLLAMA: Final = "ollama"
LLM_PROVIDERS: Final = [LLM_PROVIDER_CLAUDE, LLM_PROVIDER_OLLAMA]

# Claude access types
CLAUDE_ACCESS_API_KEY: Final = "api_key"
CLAUDE_ACCESS_SUBSCRIPTION: Final = "subscription"
CLAUDE_ACCESS_NONE: Final = "none"
CLAUDE_ACCESS_TYPES: Final = [CLAUDE_ACCESS_API_KEY, CLAUDE_ACCESS_SUBSCRIPTION, CLAUDE_ACCESS_NONE]

EMBEDDING_PROVIDER_CLAUDE: Final = "claude"
EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS: Final = "sentence_transformers"
EMBEDDING_PROVIDERS: Final = [EMBEDDING_PROVIDER_CLAUDE, EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS]

VECTOR_DB_PROVIDER_QDRANT: Final = "qdrant"
VECTOR_DB_PROVIDER_SQLITE: Final = "sqlite"
VECTOR_DB_PROVIDERS: Final = [VECTOR_DB_PROVIDER_QDRANT, VECTOR_DB_PROVIDER_SQLITE]

# Default values
DEFAULT_LLM_PROVIDER: Final = LLM_PROVIDER_CLAUDE
DEFAULT_LLM_MODEL_CLAUDE: Final = "claude-opus-4-5"
DEFAULT_LLM_MODEL_OLLAMA: Final = "neural-chat"
DEFAULT_EMBEDDING_PROVIDER: Final = EMBEDDING_PROVIDER_CLAUDE
DEFAULT_EMBEDDING_MODEL_CLAUDE: Final = "voyage-3-large"
DEFAULT_EMBEDDING_MODEL_ST: Final = "all-MiniLM-L6-v2"
DEFAULT_VECTOR_DB_PROVIDER: Final = VECTOR_DB_PROVIDER_QDRANT
DEFAULT_VECTOR_DB_HOST: Final = "localhost"
DEFAULT_VECTOR_DB_PORT: Final = 6333
DEFAULT_STORAGE_PATH: Final = "multimodal_rag"
DEFAULT_COLLECTION_NAME: Final = "documents"
DEFAULT_OLLAMA_BASE_URL: Final = "http://localhost:11434"

# Embedding dimensions
EMBEDDING_DIM_CLAUDE: Final = 3072
EMBEDDING_DIM_SENTENCE_TRANSFORMERS: Final = 384

# Chunking settings
CHUNK_SIZE_TEXT: Final = 8000      # tokens
CHUNK_OVERLAP_TEXT: Final = 200    # tokens
CHUNK_SIZE_PDF_PAGES: Final = 5    # pages per chunk
CHUNK_SIZE_IMAGE: Final = 1        # 1 chunk per image

# Search settings
DEFAULT_TOP_K: Final = 5
DEFAULT_SCORE_THRESHOLD: Final = 0.7
MAX_TOP_K: Final = 50

# Service names
SERVICE_UPLOAD_DOCUMENT: Final = "upload_document"
SERVICE_SEARCH: Final = "search"
SERVICE_REASON: Final = "reason"
SERVICE_LIST_COLLECTIONS: Final = "list_collections"
SERVICE_DELETE_DOCUMENT: Final = "delete_document"

# Supported file types
SUPPORTED_TEXT_EXTENSIONS: Final = [".txt", ".md", ".rst", ".csv", ".json"]
SUPPORTED_PDF_EXTENSIONS: Final = [".pdf"]
SUPPORTED_IMAGE_EXTENSIONS: Final = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"]
SUPPORTED_AUDIO_EXTENSIONS: Final = [".mp3", ".wav", ".flac", ".ogg", ".m4a"]  # skeleton
SUPPORTED_VIDEO_EXTENSIONS: Final = [".mp4", ".avi", ".mkv", ".mov"]  # skeleton

# Event names
EVENT_DOCUMENT_INDEXED: Final = f"{DOMAIN}_document_indexed"
EVENT_SEARCH_COMPLETED: Final = f"{DOMAIN}_search_completed"
EVENT_ERROR: Final = f"{DOMAIN}_error"

# Storage keys
STORAGE_KEY_DOCUMENTS: Final = f"{DOMAIN}_documents"
STORAGE_VERSION: Final = 1
