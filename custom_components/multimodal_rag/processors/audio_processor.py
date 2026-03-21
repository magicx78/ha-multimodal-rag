"""Audio document processor (MVP skeleton — Whisper integration planned).

This module defines the interface and structure for audio processing.
Full transcription via OpenAI Whisper will be implemented post-MVP.
The skeleton is registered so the integration gracefully reports
unsupported format rather than crashing.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from . import ProcessedDocument, ProcessorRegistry

_LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"]


class AudioProcessorNotImplementedError(NotImplementedError):
    """Raised when audio processing is attempted in MVP mode."""


async def process_audio_file(file_path: str, **kwargs: Any) -> ProcessedDocument:
    """Audio processor skeleton — NOT IMPLEMENTED in MVP.

    Planned integration:
    - Transcription: openai-whisper (local) or Whisper API
    - Speaker diarization: pyannote.audio
    - Noise reduction: noisereduce
    - Language detection: langdetect

    Args:
        file_path: Absolute path to the audio file.
        **kwargs: Future options (model, language, diarize).

    Raises:
        AudioProcessorNotImplementedError: Always in MVP mode.
    """
    file_name = os.path.basename(file_path)
    _LOGGER.warning(
        "Audio processing requested for %r but is not implemented in MVP. "
        "Whisper integration is planned for v1.1.0.",
        file_name,
    )

    # Return a placeholder document so the pipeline does not crash
    # but the user gets a clear indication of the limitation
    placeholder_text = (
        f"[Audio file: {file_name}] "
        "Audio transcription is not available in this version. "
        "Please convert to text and re-upload, or wait for v1.1.0 "
        "which will include Whisper-based transcription."
    )

    metadata = {
        "source_file": file_path,
        "file_name": file_name,
        "document_type": "audio",
        "extension": os.path.splitext(file_path)[1].lower(),
        "processed": False,
        "mvp_limitation": "audio_transcription_not_implemented",
    }

    return ProcessedDocument(
        source_file=file_path,
        document_type="audio",
        chunks=[placeholder_text],
        metadata=metadata,
        raw_text=placeholder_text,
    )


# Skeleton: Video processor (planned for v1.2.0)
async def process_video_file(file_path: str, **kwargs: Any) -> ProcessedDocument:
    """Video processor skeleton — NOT IMPLEMENTED in MVP.

    Planned integration:
    - Frame extraction: moviepy / OpenCV
    - Scene detection: PySceneDetect
    - Audio track → Whisper transcription
    - Visual description: Claude Vision per keyframe
    """
    file_name = os.path.basename(file_path)
    _LOGGER.warning(
        "Video processing requested for %r but is not implemented in MVP.", file_name
    )

    placeholder_text = (
        f"[Video file: {file_name}] "
        "Video processing is not available in this version (planned v1.2.0)."
    )

    metadata = {
        "source_file": file_path,
        "file_name": file_name,
        "document_type": "video",
        "extension": os.path.splitext(file_path)[1].lower(),
        "processed": False,
        "mvp_limitation": "video_processing_not_implemented",
    }

    return ProcessedDocument(
        source_file=file_path,
        document_type="video",
        chunks=[placeholder_text],
        metadata=metadata,
        raw_text=placeholder_text,
    )


# Register audio and video skeletons
ProcessorRegistry.register(SUPPORTED_EXTENSIONS, process_audio_file)
ProcessorRegistry.register(
    [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
    process_video_file,
)
