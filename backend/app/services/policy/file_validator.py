"""File validation service — type checking, size limits, magic byte verification."""

import logging
from dataclasses import dataclass

from app.core.exceptions import BadRequestError

logger = logging.getLogger("societyos.policy.validator")

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

# Magic bytes for file type verification
MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"PK\x03\x04": "docx",  # ZIP-based (DOCX, XLSX, etc.)
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".doc"}


@dataclass
class ValidatedFile:
    """Result of file validation."""

    content: bytes
    filename: str
    detected_type: str  # "pdf", "docx", "txt"
    size_bytes: int


def validate_upload(content: bytes, filename: str | None, content_type: str | None) -> ValidatedFile:
    """Validate an uploaded file for policy extraction.

    Checks:
    1. File is not empty.
    2. File size within limits.
    3. File extension is allowed.
    4. Magic bytes match declared type.

    Returns ValidatedFile or raises BadRequestError.
    """
    filename = filename or "unknown"

    # 1. Empty check
    if not content or len(content) < 10:
        raise BadRequestError("Uploaded file is empty or too small")

    # 2. Size check
    if len(content) > MAX_FILE_SIZE:
        raise BadRequestError(f"File too large ({len(content) / 1024 / 1024:.1f} MB). Maximum is 50 MB.")

    # 3. Extension check
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext and ext not in ALLOWED_EXTENSIONS:
        raise BadRequestError(
            f"Unsupported file type '{ext}'. Allowed: PDF, DOCX, TXT."
        )

    # 4. Magic byte detection
    detected_type = _detect_type(content, ext, content_type)

    logger.info(
        "File validated: %s (%s, %d bytes, detected=%s)",
        filename, content_type, len(content), detected_type,
    )

    return ValidatedFile(
        content=content,
        filename=filename,
        detected_type=detected_type,
        size_bytes=len(content),
    )


def _detect_type(content: bytes, ext: str, content_type: str | None) -> str:
    """Detect actual file type from magic bytes, falling back to extension."""
    # Check magic bytes
    for magic, ftype in MAGIC_BYTES.items():
        if content[:len(magic)] == magic:
            # Verify DOCX vs other ZIP formats
            if ftype == "docx" and ext == ".pdf":
                raise BadRequestError("File has .pdf extension but is a ZIP archive")
            return ftype

    # Check content-type header
    if content_type:
        if "pdf" in content_type:
            return "pdf"
        if "wordprocessingml" in content_type or "msword" in content_type:
            return "docx"

    # Fall back to extension
    type_map = {".pdf": "pdf", ".docx": "docx", ".doc": "docx", ".txt": "txt"}
    if ext in type_map:
        return type_map[ext]

    # Try to decode as text
    try:
        content[:1000].decode("utf-8")
        return "txt"
    except UnicodeDecodeError:
        raise BadRequestError("Cannot determine file type. Please upload a PDF, DOCX, or TXT file.")
