"""PDF document processor using PyMuPDF."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from . import ProcessedDocument, ProcessorRegistry

_LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = [".pdf"]
PAGES_PER_CHUNK = 5


async def process_pdf_file(file_path: str, **kwargs: Any) -> ProcessedDocument:
    """Extract text and images from a PDF using PyMuPDF.

    Processes pages in groups of PAGES_PER_CHUNK to create
    semantically coherent chunks. Also extracts embedded images
    for potential vision processing.

    Args:
        file_path: Absolute path to the PDF file.
        **kwargs: Optional overrides (pages_per_chunk, extract_images).

    Returns:
        ProcessedDocument with text chunks and extracted images.
    """
    pages_per_chunk = kwargs.get("pages_per_chunk", PAGES_PER_CHUNK)
    extract_images = kwargs.get("extract_images", True)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        _extract_pdf_sync,
        file_path,
        pages_per_chunk,
        extract_images,
    )
    return result


def _extract_pdf_sync(
    file_path: str,
    pages_per_chunk: int,
    extract_images: bool,
) -> ProcessedDocument:
    """Synchronous PDF extraction (runs in thread pool).

    Args:
        file_path: PDF file path.
        pages_per_chunk: Number of pages per text chunk.
        extract_images: Whether to extract embedded images.

    Returns:
        ProcessedDocument.
    """
    try:
        import fitz  # PyMuPDF  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF is required for PDF processing. pip install PyMuPDF"
        ) from exc

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        _LOGGER.error("Failed to open PDF %r: %s", file_path, exc)
        raise

    file_name = os.path.basename(file_path)
    page_count = len(doc)

    # Extract metadata from PDF
    pdf_meta = doc.metadata or {}
    metadata = {
        "source_file": file_path,
        "file_name": file_name,
        "document_type": "pdf",
        "extension": ".pdf",
        "page_count": page_count,
        "title": pdf_meta.get("title", ""),
        "author": pdf_meta.get("author", ""),
        "creation_date": pdf_meta.get("creationDate", ""),
        "subject": pdf_meta.get("subject", ""),
    }

    # Extract text page by page, group into chunks
    all_text_parts: list[str] = []
    chunks: list[str] = []
    current_chunk_parts: list[str] = []
    current_page_count = 0

    for page_num in range(page_count):
        page = doc.load_page(page_num)
        page_text = page.get_text("text")  # type: ignore[attr-defined]

        if page_text.strip():
            header = f"[Page {page_num + 1}]"
            current_chunk_parts.append(f"{header}\n{page_text.strip()}")
            all_text_parts.append(page_text.strip())

        current_page_count += 1

        if current_page_count >= pages_per_chunk:
            chunk_text = "\n\n".join(current_chunk_parts).strip()
            if chunk_text:
                chunks.append(chunk_text)
            current_chunk_parts = []
            current_page_count = 0

    # Flush remaining pages
    if current_chunk_parts:
        chunk_text = "\n\n".join(current_chunk_parts).strip()
        if chunk_text:
            chunks.append(chunk_text)

    raw_text = "\n\n".join(all_text_parts)

    # Extract images if requested
    image_bytes_list: list[bytes] = []
    if extract_images:
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes_list.append(base_image["image"])
                except Exception as img_exc:
                    _LOGGER.debug(
                        "Could not extract image xref=%d from page %d: %s",
                        xref, page_num + 1, img_exc,
                    )

    doc.close()
    metadata["extracted_images"] = len(image_bytes_list)

    _LOGGER.info(
        "Processed PDF %r: %d pages → %d chunks, %d images extracted",
        file_name, page_count, len(chunks), len(image_bytes_list),
    )

    return ProcessedDocument(
        source_file=file_path,
        document_type="pdf",
        chunks=chunks,
        metadata=metadata,
        images=image_bytes_list,
        raw_text=raw_text,
    )


# Register processor
ProcessorRegistry.register(SUPPORTED_EXTENSIONS, process_pdf_file)
