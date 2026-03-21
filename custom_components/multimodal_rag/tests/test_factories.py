"""Unit tests for the plugin factory system."""
from __future__ import annotations

import pytest

from ..llm.base import LLMProvider, LLMResponse
from ..llm.factory import LLMFactory
from ..embeddings.base import EmbeddingProvider, EmbeddingResult
from ..embeddings.factory import EmbeddingFactory
from ..db.base import VectorDBProvider
from ..db.factory import VectorDBFactory


# ── Minimal stub implementations for testing ─────────────────────────────────

class _StubLLM(LLMProvider):
    async def generate(self, prompt, context=""):
        return LLMResponse("stub", "stub-model", "stub")

    async def reason(self, query, context):
        return LLMResponse("stub", "stub-model", "stub")

    async def health_check(self):
        return True


class _StubEmbedder(EmbeddingProvider):
    @property
    def dimension(self):
        return 4

    async def embed(self, text):
        return [0.1, 0.2, 0.3, 0.4]

    async def embed_batch(self, texts):
        return EmbeddingResult(
            vectors=[[0.1, 0.2, 0.3, 0.4]] * len(texts),
            model="stub",
            provider="stub",
            dimension=4,
        )

    async def health_check(self):
        return True


# ── LLMFactory tests ─────────────────────────────────────────────────────────

class TestLLMFactory:
    """Tests for LLMFactory plugin registry."""

    def test_register_and_create(self):
        """Registered provider should be instantiable."""
        LLMFactory.register("_stub_llm_test", _StubLLM)
        provider = LLMFactory.create("_stub_llm_test", model="test-model")
        assert isinstance(provider, _StubLLM)
        assert provider.model == "test-model"

    def test_create_unknown_raises(self):
        """Creating an unregistered provider should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMFactory.create("definitely_not_registered_xyz")

    def test_register_non_subclass_raises(self):
        """Registering a non-LLMProvider class should raise TypeError."""
        with pytest.raises(TypeError):
            LLMFactory.register("bad", object)  # type: ignore

    def test_available_providers_includes_registered(self):
        """Available providers list should include freshly registered names."""
        LLMFactory.register("_check_available_test", _StubLLM)
        assert "_check_available_test" in LLMFactory.available_providers()

    def test_is_registered(self):
        """is_registered should return True only for known providers."""
        LLMFactory.register("_is_reg_test", _StubLLM)
        assert LLMFactory.is_registered("_is_reg_test") is True
        assert LLMFactory.is_registered("nonexistent_xyz") is False


# ── EmbeddingFactory tests ───────────────────────────────────────────────────

class TestEmbeddingFactory:
    """Tests for EmbeddingFactory plugin registry."""

    def test_register_and_create(self):
        """Registered embedder should be instantiable."""
        EmbeddingFactory.register("_stub_embed_test", _StubEmbedder)
        provider = EmbeddingFactory.create("_stub_embed_test", model="stub-model")
        assert isinstance(provider, _StubEmbedder)
        assert provider.dimension == 4

    def test_create_unknown_raises(self):
        """Creating an unregistered provider should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            EmbeddingFactory.create("xyz_not_registered")

    def test_register_non_subclass_raises(self):
        """Only EmbeddingProvider subclasses should be accepted."""
        with pytest.raises(TypeError):
            EmbeddingFactory.register("bad", int)  # type: ignore


# ── Auto-registration tests ──────────────────────────────────────────────────

class TestAutoRegistration:
    """Tests that providers auto-register when their modules are imported."""

    def test_claude_llm_auto_registered(self):
        """Claude LLM should be registered after importing the module."""
        import importlib
        import custom_components.multimodal_rag.llm.claude as _  # noqa: F401
        assert LLMFactory.is_registered("claude")

    def test_ollama_llm_auto_registered(self):
        """Ollama LLM should be registered after importing."""
        import custom_components.multimodal_rag.llm.ollama as _  # noqa: F401
        assert LLMFactory.is_registered("ollama")

    def test_qdrant_db_auto_registered(self):
        """Qdrant DB should be registered after importing."""
        import custom_components.multimodal_rag.db.qdrant_db as _  # noqa: F401
        assert VectorDBFactory.is_registered("qdrant")

    def test_sqlite_db_auto_registered(self):
        """SQLite DB should be registered after importing."""
        import custom_components.multimodal_rag.db.sqlite_db as _  # noqa: F401
        assert VectorDBFactory.is_registered("sqlite")
