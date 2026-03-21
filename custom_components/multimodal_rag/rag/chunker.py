"""Content-aware text chunker for RAG indexing."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

# Default chunking parameters
DEFAULT_CHUNK_SIZE = 8000    # characters (approx 2000 tokens at ~4 chars/token)
DEFAULT_CHUNK_OVERLAP = 400  # characters
MIN_CHUNK_SIZE = 50          # Discard chunks shorter than this


@dataclass
class Chunk:
    """A single text chunk with positional metadata."""

    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TextChunker:
    """Content-aware text chunker.

    Splits text into overlapping windows, preferring to break at
    paragraph, sentence, or word boundaries to preserve semantic
    coherence.

    Chunking strategy by document type:
    - text: character-based windows with sentence-boundary alignment
    - pdf: handled at page group level (PDF processor), then re-chunked if large
    - image: 1 chunk per image (no further splitting)
    - audio: transcript treated as text (planned)
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """Initialize the chunker.

        Args:
            chunk_size: Target chunk size in characters.
            chunk_overlap: Overlap between consecutive chunks in characters.
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into overlapping chunks.

        Tries to break at paragraph boundaries first, then sentence
        boundaries, finally at word boundaries.

        Args:
            text: Input text string.
            metadata: Optional metadata to attach to each chunk.

        Returns:
            List of Chunk objects.
        """
        if not text or not text.strip():
            return []

        text = text.strip()
        base_meta = metadata or {}

        # If text fits in a single chunk, return as-is
        if len(text) <= self._chunk_size:
            return [
                Chunk(
                    text=text,
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata=dict(base_meta),
                )
            ]

        chunks: list[Chunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self._chunk_size

            if end >= len(text):
                # Last chunk
                chunk_text = text[start:].strip()
                if len(chunk_text) >= MIN_CHUNK_SIZE:
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            index=chunk_index,
                            start_char=start,
                            end_char=len(text),
                            metadata=dict(base_meta),
                        )
                    )
                break

            # Try to find a good break point
            break_point = self._find_break_point(text, start, end)

            chunk_text = text[start:break_point].strip()
            if len(chunk_text) >= MIN_CHUNK_SIZE:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=chunk_index,
                        start_char=start,
                        end_char=break_point,
                        metadata=dict(base_meta),
                    )
                )
                chunk_index += 1

            # Advance with overlap
            start = max(break_point - self._chunk_overlap, start + 1)

        _LOGGER.debug(
            "Chunked %d chars into %d chunks (size=%d, overlap=%d)",
            len(text), len(chunks), self._chunk_size, self._chunk_overlap,
        )
        return chunks

    def chunk_documents(
        self, raw_chunks: list[str], metadata: dict | None = None
    ) -> list[Chunk]:
        """Chunk a list of pre-split document sections.

        Used for PDFs where the processor already groups pages into chunks.
        Each section is re-chunked if it exceeds chunk_size.

        Args:
            raw_chunks: List of text sections from document processor.
            metadata: Metadata to attach to all output chunks.

        Returns:
            Flat list of Chunk objects.
        """
        all_chunks: list[Chunk] = []
        global_index = 0

        for section_idx, section in enumerate(raw_chunks):
            section_meta = dict(metadata or {})
            section_meta["section_index"] = section_idx

            section_chunks = self.chunk_text(section, metadata=section_meta)
            for chunk in section_chunks:
                chunk.index = global_index
                all_chunks.append(chunk)
                global_index += 1

        return all_chunks

    def _find_break_point(self, text: str, start: int, target_end: int) -> int:
        """Find the best break point near target_end.

        Priority: paragraph break > sentence break > word break > hard cut.

        Args:
            text: Full text.
            start: Current chunk start.
            target_end: Desired end position.

        Returns:
            Best break position index.
        """
        window = text[start:target_end]
        search_start = max(0, len(window) - 500)  # Look back up to 500 chars

        # 1. Try paragraph break (\n\n)
        para_match = None
        for m in re.finditer(r"\n\n+", window[search_start:]):
            para_match = m
        if para_match:
            return start + search_start + para_match.end()

        # 2. Try sentence break (. ! ? followed by whitespace)
        sentence_match = None
        for m in re.finditer(r"[.!?]\s+", window[search_start:]):
            sentence_match = m
        if sentence_match:
            return start + search_start + sentence_match.end()

        # 3. Try word boundary (space)
        word_match = None
        for m in re.finditer(r"\s+", window[search_start:]):
            word_match = m
        if word_match:
            return start + search_start + word_match.end()

        # 4. Hard cut
        return target_end
