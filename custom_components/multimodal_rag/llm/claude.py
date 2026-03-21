"""Claude (Anthropic) LLM provider implementation."""
from __future__ import annotations

import logging
from typing import Any

from .base import LLMProvider, LLMResponse
from .factory import LLMFactory

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT_REASON = """You are a knowledgeable Home Assistant assistant with access to a \
personal document knowledge base. Answer questions accurately and concisely based \
on the provided context. If the context does not contain sufficient information, \
say so clearly rather than guessing. Always cite the source document when possible."""

SYSTEM_PROMPT_GENERATE = """You are a helpful assistant integrated with Home Assistant. \
Respond clearly and concisely."""


class ClaudeProvider(LLMProvider):
    """LLM provider backed by Anthropic Claude API.

    Supports both generation and retrieval-augmented reasoning.
    Uses the official anthropic async client for non-blocking I/O.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> None:
        """Initialize the Claude provider.

        Args:
            model: Claude model identifier (e.g. "claude-opus-4-5").
            api_key: Anthropic API key.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0 = deterministic).
        """
        super().__init__(model=model, **kwargs)
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily create and cache the Anthropic async client."""
        if self._client is None:
            try:
                import anthropic  # noqa: PLC0415
                self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            except ImportError as exc:
                raise ImportError(
                    "anthropic package is required for Claude provider. "
                    "Install it with: pip install anthropic"
                ) from exc
        return self._client

    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        """Generate a Claude completion.

        Args:
            prompt: User prompt.
            context: Optional RAG context prepended to the prompt.

        Returns:
            LLMResponse with generated content.
        """
        client = self._get_client()
        user_content = f"Context:\n{context}\n\n{prompt}" if context else prompt

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT_GENERATE,
                messages=[{"role": "user", "content": user_content}],
            )
            content = response.content[0].text
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            _LOGGER.debug(
                "Claude generate: %d tokens used (model=%s)", usage["total_tokens"], self.model
            )
            return LLMResponse(
                content=content,
                model=self.model,
                provider="claude",
                usage=usage,
            )
        except Exception as exc:
            _LOGGER.error("Claude generate error: %s", exc)
            raise

    async def reason(self, query: str, context: str) -> LLMResponse:
        """Answer a question by reasoning over retrieved document context.

        Args:
            query: User's question.
            context: Concatenated document chunks from vector search.

        Returns:
            LLMResponse with the answer and source attribution hints.
        """
        client = self._get_client()
        user_content = (
            f"Retrieved Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            "Please answer the question based on the retrieved context above. "
            "If the answer is not in the context, state that clearly."
        )

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT_REASON,
                messages=[{"role": "user", "content": user_content}],
            )
            content = response.content[0].text
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            _LOGGER.debug(
                "Claude reason: %d tokens used (model=%s)", usage["total_tokens"], self.model
            )
            return LLMResponse(
                content=content,
                model=self.model,
                provider="claude",
                usage=usage,
            )
        except Exception as exc:
            _LOGGER.error("Claude reason error: %s", exc)
            raise

    async def health_check(self) -> bool:
        """Ping Claude API to verify connectivity and API key validity."""
        try:
            client = self._get_client()
            response = await client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return bool(response.content)
        except Exception as exc:
            _LOGGER.warning("Claude health check failed: %s", exc)
            return False


# Auto-register this provider
LLMFactory.register("claude", ClaudeProvider)
