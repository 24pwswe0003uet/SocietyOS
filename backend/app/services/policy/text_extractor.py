"""Text extraction service — pulls readable text from PDF, DOCX, URL, and plain text files."""

import io
import logging
from dataclasses import dataclass

import httpx

from app.core.exceptions import BadRequestError
from app.services.policy.file_validator import ValidatedFile

logger = logging.getLogger("societyos.policy.extractor")


@dataclass
class ExtractedDocument:
    """Result of text extraction with metadata."""

    text: str
    page_count: int | None
    char_count: int
    source_type: str  # "pdf", "docx", "txt", "url"
    pages: list[dict] | None = None  # [{"page": 1, "text": "...", "char_count": 123}]


def extract_text(validated_file: ValidatedFile) -> ExtractedDocument:
    """Extract readable text from a validated file.

    Dispatches to the appropriate extractor based on detected type.
    """
    extractors = {
        "pdf": _extract_pdf,
        "docx": _extract_docx,
        "txt": _extract_txt,
    }

    extractor = extractors.get(validated_file.detected_type)
    if not extractor:
        raise BadRequestError(f"No extractor for type: {validated_file.detected_type}")

    result = extractor(validated_file.content)

    if result.char_count < 50:
        logger.warning("Extraction yielded very little text (%d chars)", result.char_count)

    logger.info(
        "Extracted %d chars from %s (%s, %s pages)",
        result.char_count,
        validated_file.filename,
        result.source_type,
        result.page_count or "N/A",
    )

    return result


def _extract_pdf(content: bytes) -> ExtractedDocument:
    """Extract text from a PDF using PyMuPDF, falling back to pdfplumber."""
    pages = []

    try:
        import pymupdf
        doc = pymupdf.open(stream=content, filetype="pdf")
        for i, page in enumerate(doc):
            page_text = page.get_text("text")
            pages.append({"page": i + 1, "text": page_text, "char_count": len(page_text)})
        doc.close()
    except Exception as e:
        logger.warning("PyMuPDF failed, trying pdfplumber: %s", e)
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    pages.append({"page": i + 1, "text": page_text, "char_count": len(page_text)})
        except Exception as e2:
            logger.error("Both PDF extractors failed: %s", e2)
            raise BadRequestError("Could not extract text from this PDF. It may be scanned or corrupted.")

    full_text = "\n\n".join(p["text"] for p in pages if p["text"].strip())
    return ExtractedDocument(
        text=full_text,
        page_count=len(pages),
        char_count=len(full_text),
        source_type="pdf",
        pages=pages,
    )


def _extract_docx(content: bytes) -> ExtractedDocument:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))

        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        full_text = "\n\n".join(paragraphs)
        return ExtractedDocument(
            text=full_text,
            page_count=None,  # DOCX doesn't have fixed pages
            char_count=len(full_text),
            source_type="docx",
        )
    except Exception as e:
        logger.error("DOCX extraction failed: %s", e)
        raise BadRequestError("Could not extract text from this DOCX file.")


def _extract_txt(content: bytes) -> ExtractedDocument:
    """Extract text from a plain text file."""
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        text = content.decode("latin-1", errors="replace")

    return ExtractedDocument(
        text=text,
        page_count=None,
        char_count=len(text),
        source_type="txt",
    )


async def extract_from_url(url: str) -> ExtractedDocument:
    """Fetch a URL and extract text content.

    Supports plain HTML pages (strips tags) and direct PDF/DOCX links.
    """
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise BadRequestError(f"Could not fetch URL: {e}")

    content_type = resp.headers.get("content-type", "")

    # PDF link
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        from app.services.policy.file_validator import ValidatedFile
        vf = ValidatedFile(content=resp.content, filename="url_document.pdf",
                          detected_type="pdf", size_bytes=len(resp.content))
        return extract_text(vf)

    # DOCX link
    if "wordprocessingml" in content_type or url.lower().endswith(".docx"):
        from app.services.policy.file_validator import ValidatedFile
        vf = ValidatedFile(content=resp.content, filename="url_document.docx",
                          detected_type="docx", size_bytes=len(resp.content))
        return extract_text(vf)

    # HTML — strip tags crudely
    import re
    text = resp.text
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return ExtractedDocument(
        text=text,
        page_count=None,
        char_count=len(text),
        source_type="url",
    )
