"""Image document processor with Claude Vision integration."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
from typing import Any

from . import ProcessedDocument, ProcessorRegistry

_LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"]

# Maximum image dimensions for API submission
MAX_IMAGE_DIMENSION = 2048
# Claude Vision supported MIME types
_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/png",   # Convert BMP to PNG
    ".tiff": "image/png",
    ".tif": "image/png",
}


async def process_image_file(file_path: str, **kwargs: Any) -> ProcessedDocument:
    """Process an image file using Claude Vision for description and OCR.

    Loads the image with Pillow, resizes if needed for API limits,
    then sends to Claude Vision API for a detailed description
    that becomes the searchable text representation.

    Args:
        file_path: Absolute path to the image file.
        **kwargs: Optional overrides (api_key, model, describe_only).

    Returns:
        ProcessedDocument where chunks contain the image description.
    """
    api_key = kwargs.get("api_key", "")
    model = kwargs.get("model", "claude-opus-4-5")
    describe_only = kwargs.get("describe_only", False)

    loop = asyncio.get_event_loop()

    # Load and prepare image in thread pool
    image_bytes, mime_type, img_metadata = await loop.run_in_executor(
        None, _load_and_prepare_image, file_path
    )

    # Generate description via Claude Vision
    description = ""
    if api_key and not describe_only:
        try:
            description = await _describe_with_claude(
                image_bytes=image_bytes,
                mime_type=mime_type,
                api_key=api_key,
                model=model,
                file_name=os.path.basename(file_path),
            )
        except Exception as exc:
            _LOGGER.warning(
                "Claude Vision failed for %r, using filename only: %s",
                file_path, exc,
            )
            description = f"Image file: {os.path.basename(file_path)}"
    else:
        description = f"Image file: {os.path.basename(file_path)}"

    file_name = os.path.basename(file_path)
    metadata = {
        "source_file": file_path,
        "file_name": file_name,
        "document_type": "image",
        "extension": os.path.splitext(file_path)[1].lower(),
        **img_metadata,
    }

    _LOGGER.info("Processed image %r: %d chars description", file_name, len(description))

    return ProcessedDocument(
        source_file=file_path,
        document_type="image",
        chunks=[description] if description else [],
        metadata=metadata,
        images=[image_bytes],
        raw_text=description,
    )


def _load_and_prepare_image(
    file_path: str,
) -> tuple[bytes, str, dict[str, Any]]:
    """Load image with Pillow, resize if needed, return bytes + metadata.

    Args:
        file_path: Image file path.

    Returns:
        Tuple of (image_bytes, mime_type, metadata_dict).
    """
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("Pillow is required for image processing. pip install Pillow") from exc

    ext = os.path.splitext(file_path)[1].lower()
    mime_type = _MIME_MAP.get(ext, "image/jpeg")

    img = Image.open(file_path)
    original_size = img.size
    original_mode = img.mode

    # Convert to RGB for API compatibility (handles RGBA, L, P modes)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize if too large
    max_dim = MAX_IMAGE_DIMENSION
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)  # type: ignore[attr-defined]
        _LOGGER.debug("Resized image from %s to %s", original_size, new_size)

    # Serialize to bytes
    output = io.BytesIO()
    save_format = "JPEG" if mime_type == "image/jpeg" else "PNG"
    img.save(output, format=save_format, quality=85)
    image_bytes = output.getvalue()

    metadata = {
        "original_width": original_size[0],
        "original_height": original_size[1],
        "color_mode": original_mode,
        "processed_width": img.width,
        "processed_height": img.height,
        "file_size_bytes": os.path.getsize(file_path),
    }

    return image_bytes, mime_type, metadata


async def _describe_with_claude(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
    model: str,
    file_name: str,
) -> str:
    """Use Claude Vision API to generate an image description.

    Args:
        image_bytes: Raw image bytes.
        mime_type: MIME type string.
        api_key: Anthropic API key.
        model: Claude model to use.
        file_name: Original filename for context.

    Returns:
        Descriptive text string.
    """
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("anthropic package required. pip install anthropic") from exc

    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Please provide a detailed description of this image (file: {file_name}). "
                            "Include: visual content, any text visible (OCR), colors, objects, "
                            "people, diagrams, charts, or any other relevant details. "
                            "This description will be used for semantic search."
                        ),
                    },
                ],
            }
        ],
    )
    return response.content[0].text


# Register processor
ProcessorRegistry.register(SUPPORTED_EXTENSIONS, process_image_file)
