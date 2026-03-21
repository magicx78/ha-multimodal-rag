"""Ollama LLM provider implementation (local fallback)."""
from __future__ import annotations

import logging
from typing import Any

from .base import LLMProvider, LLMResponse
from .factory import LLMFactory

_LOGGER = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"

SYSTEM_PROMPT_REASON = (
    "You are a helpful assistant. Answer the user's question based solely on "
    "the provided context. If the context is insufficient, say so."
)


class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama instance.

    Acts as the fallback when Claude API is unavailable or not configured.
    Uses the official ollama Python client for async-compatible requests.
    """

    def __init__(
        self,
        model: str,
        base_url: str = DEFAULT_BASE_URL,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> None:
        """Initialize the Ollama provider.

        Args:
            model: Ollama model name (e.g. "neural-chat", "llama3").
            base_url: Ollama server URL (default localhost:11434).
            temperature: Sampling temperature.
        """
        super().__init__(model=model, **kwargs)
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily create the Ollama async client."""
        if self._client is None:
            try:
                import ollama  # noqa: PLC0415
                self._client = ollama.AsyncClient(host=self._base_url)
            except ImportError as exc:
                raise ImportError(
                    "ollama package is required for Ollama provider. "
                    "Install it with: pip install ollama"
                ) from exc
        return self._client

    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        """Generate a completion via Ollama.

        Args:
            prompt: User prompt.
            context: Optional RAG context.

        Returns:
            LLMResponse with generated content.
        """
        client = self._get_client()
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"Use the following context to assist:\n{context}",
            })
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": self._temperature},
            )
            content = response["message"]["content"]
            _LOGGER.debug("Ollama generate: model=%s", self.model)
            return LLMResponse(
                content=content,
                model=self.model,
                provider="ollama",
                usage={},
            )
        except Exception as exc:
            _LOGGER.error("Ollama generate error: %s", exc)
            raise

    async def reason(self, query: str, context: str) -> LLMResponse:
        """Answer a question over retrieved context using Ollama.

        Args:
            query: The user's question.
            context: Retrieved document chunks.

        Returns:
            LLMResponse with the answer.
        """
        client = self._get_client()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_REASON},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {query}"
                ),
            },
        ]

        try:
            response = await client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": self._temperature},
            )
            content = response["message"]["content"]
            _LOGGER.debug("Ollama reason: model=%s", self.model)
            return LLMResponse(
                content=content,
                model=self.model,
                provider="ollama",
                usage={},
            )
        except Exception as exc:
            _LOGGER.error("Ollama reason error: %s", exc)
            raise

    async def health_check(self) -> bool:
        """Verify Ollama is running and the model is available."""
        try:
            client = self._get_client()
            # List local models — if this succeeds, Ollama is up
            models_response = await client.list()
            available = [m["name"] for m in models_response.get("models", [])]
            if self.model not in available and not any(
                self.model in m for m in available
            ):
                _LOGGER.warning(
                    "Ollama model %r not found locally. Available: %s",
                    self.model, available,
                )
                return False
            return True
        except Exception as exc:
            _LOGGER.warning("Ollama health check failed: %s", exc)
            return False


# Auto-register this provider
LLMFactory.register("ollama", OllamaProvider)
