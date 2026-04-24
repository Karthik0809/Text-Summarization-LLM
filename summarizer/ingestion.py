"""Ingest text from PDF files and web URLs."""
from __future__ import annotations

import io
import logging
import re

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_from_pdf(file_bytes: bytes) -> str:
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("Install pdfplumber: pip install pdfplumber") from e

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return clean_text("\n".join(pages))


def extract_from_url(url: str) -> tuple[str, str]:
    """Return (title, body_text) extracted from a web URL."""
    try:
        import trafilatura
    except ImportError as e:
        raise ImportError("Install trafilatura: pip install trafilatura") from e

    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        raise ValueError(f"Could not fetch: {url}")

    text = trafilatura.extract(downloaded)
    metadata = trafilatura.extract_metadata(downloaded)
    title = (metadata.title if metadata and metadata.title else url)
    return title, clean_text(text or "")
