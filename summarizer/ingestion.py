"""Ingest text from PDF files and web URLs, with multi-method fallback."""
from __future__ import annotations

import io
import logging
import re

logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "DNT": "1",
}


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
    text = clean_text("\n".join(pages))
    if not text:
        raise ValueError("PDF appears to be empty or image-based (no selectable text).")
    return text


def _try_trafilatura(url: str) -> tuple[str, str] | None:
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        if not text or len(text.split()) < 30:
            return None
        metadata = trafilatura.extract_metadata(downloaded)
        title = metadata.title if (metadata and metadata.title) else url
        return title, clean_text(text)
    except Exception as exc:
        logger.debug("trafilatura failed: %s", exc)
        return None


def _try_requests_bs4(url: str) -> tuple[str, str] | None:
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title: prefer og:title meta tag
        og_title = soup.find("meta", property="og:title")
        title_tag = soup.find("title")
        title = (
            (og_title.get("content", "").strip() if og_title else None)
            or (title_tag.get_text(strip=True) if title_tag else None)
            or url
        )

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "noscript", "iframe", "form"]):
            tag.decompose()

        # Priority: <article> → class hint → <main> → <body>
        content = (
            soup.find("article")
            or soup.find("div", {"class": re.compile(r"article|content|story|post-body", re.I)})
            or soup.find("main")
            or soup.find("body")
        )
        if content:
            paragraphs = content.find_all("p")
            text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs) if paragraphs \
                else content.get_text(separator=" ", strip=True)
            if text and len(text.split()) >= 30:
                return title, clean_text(text)
        return None
    except Exception as exc:
        logger.debug("requests/bs4 failed: %s", exc)
        return None


def extract_from_url(url: str) -> tuple[str, str]:
    """Return (title, body_text).  Tries trafilatura first, then requests+BS4."""
    result = _try_trafilatura(url) or _try_requests_bs4(url)
    if result:
        return result
    raise ValueError(
        "Could not extract article text from this URL. "
        "Possible reasons: the page requires JavaScript (e.g. MSN, Twitter, LinkedIn), "
        "the site blocks automated access (403/paywalled), "
        "or the URL points to a video or image. "
        "Tip: Open the article, select all text (Ctrl+A), copy it, and paste into the Text tab."
    )
