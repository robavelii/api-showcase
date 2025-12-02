"""File Processor schemas."""

from apps.file_processor.schemas.file import (
    FileMetadata,
    SignedUrlRequest,
    SignedUrlResponse,
    UploadResponse,
)
from apps.file_processor.schemas.conversion import (
    ConversionRequest,
    ConversionJobResponse,
    ConversionStatusResponse,
    ConversionWebhookPayload,
)

__all__ = [
    "FileMetadata",
    "SignedUrlRequest",
    "SignedUrlResponse",
    "UploadResponse",
    "ConversionRequest",
    "ConversionJobResponse",
    "ConversionStatusResponse",
    "ConversionWebhookPayload",
]
