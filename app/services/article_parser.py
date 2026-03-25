"""Article parser service.

Fetches and parses article content from a URL using trafilatura (primary)
with a BeautifulSoup fallback. Returns structured ParsedArticle.
"""
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

FETCH_TIMEOUT = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en,*;q=0.5",
}


@dataclass
class ParsedArticle:
    url: str
    title: str
    publisher: str
    published_at: Optional[str]
    raw_content: str
    cleaned_content: str
    language: str


class ArticleParseError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ArticleParser:
    def parse(self, url: str) -> ParsedArticle:
        self._validate_url(url)
        return self._fetch_and_parse(url)

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ArticleParseError("ART_001", f"Invalid URL scheme: {parsed.scheme}")
        if not parsed.netloc:
            raise ArticleParseError("ART_001", "URL has no host")

    def _fetch_and_parse(self, url: str) -> ParsedArticle:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise ArticleParseError("ART_001", f"Request timed out: {url}")
        except requests.exceptions.HTTPError as e:
            raise ArticleParseError("ART_001", f"HTTP error {e.response.status_code}: {url}")
        except requests.exceptions.RequestException as e:
            raise ArticleParseError("ART_001", f"Failed to fetch article: {e}")

        html = resp.text

        # Primary: trafilatura (best for news articles)
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=False,
        )

        # Fallback: BeautifulSoup
        if not extracted or len(extracted.strip()) < 100:
            extracted = self._bs4_extract(html)

        if not extracted or len(extracted.strip()) < 50:
            raise ArticleParseError("ART_002", "Article body could not be extracted (too short or empty)")

        # Extract metadata
        metadata = trafilatura.extract_metadata(html, default_url=url)
        title = (metadata.title if metadata and metadata.title else "") or self._bs4_title(html)
        publisher = (
            (metadata.sitename if metadata and metadata.sitename else "")
            or urlparse(url).netloc
        )
        published_at = None
        if metadata and metadata.date:
            published_at = str(metadata.date)

        return ParsedArticle(
            url=url,
            title=title or urlparse(url).netloc,
            publisher=publisher,
            published_at=published_at,
            raw_content=html[:5000],  # keep raw short to avoid bloat
            cleaned_content=extracted,
            language=self._detect_language(extracted),
        )

    def _bs4_extract(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def _bs4_title(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("title")
        return tag.get_text(strip=True) if tag else ""

    def _detect_language(self, text: str) -> str:
        # Simple heuristic: check for CJK characters
        cjk_count = sum(1 for c in text[:500] if "\u3000" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7a3")
        if cjk_count > 20:
            # Distinguish Japanese (hiragana/katakana) vs Korean (hangul)
            ja_count = sum(1 for c in text[:500] if "\u3040" <= c <= "\u30ff")
            ko_count = sum(1 for c in text[:500] if "\uac00" <= c <= "\ud7a3")
            return "ja" if ja_count >= ko_count else "ko"
        return "en"
