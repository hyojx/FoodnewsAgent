"""Search service.

Uses DuckDuckGo (no API key required) to search the web.
Fetches snippet content from top results using requests + trafilatura.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

import requests
import trafilatura
from duckduckgo_search import DDGS

FETCH_TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,ko;q=0.9,en;q=0.8",
}


@dataclass
class SearchResult:
    url: str
    title: str
    publisher: str
    published_at: Optional[str]
    snippet: str
    full_content: str = ""
    source_type: str = "article"
    language: str = "ja"
    relevance_score: float = 0.8


class SearchService:
    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        return self._execute_search(query, limit)

    def search_for_field(
        self, field_path: str, topic: str, category: str, limit: int = 3
    ) -> List[SearchResult]:
        queries = self._generate_queries(field_path, topic, category)
        results = []
        seen_urls = set()
        for q in queries[:2]:
            for r in self._execute_search(q, limit):
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    results.append(r)
        return results[:limit]

    def _generate_queries(self, field_path: str, topic: str, category: str) -> List[str]:
        query_templates = {
            "cases": [f"{topic} 事例 ブランド", f"{topic} 企業 活用事例"],
            "trend_name": [f"{topic} トレンド 定義"],
            "definition": [f"{topic} とは 意味 定義"],
            "change_from_previous": [f"{topic} 変化 従来比較"],
            "background": [f"{topic} 背景 歴史"],
            "expansion_pattern.geographic_scope": [f"{topic} グローバル展開 地域"],
            "expansion_pattern.industry_expansion": [f"{topic} 業界 拡大"],
            "key_features": [f"{topic} 特徴 機能"],
            "how_it_works": [f"{topic} 仕組み 方法"],
            "business_model.pricing": [f"{topic} 価格 料金"],
            "business_model.model": [f"{topic} ビジネスモデル 収益"],
            "technology_principle": [f"{topic} 技術 原理 仕組み"],
            "applications": [f"{topic} 応用 活用 企業"],
            "results_and_effects": [f"{topic} 効果 結果 実績"],
            "industry_meaning": [f"{topic} 業界 意義 影響"],
        }
        base = field_path.split("[")[0]
        return query_templates.get(base, [f"{topic} {field_path.replace('.', ' ')}"])

    def _execute_search(self, query: str, limit: int) -> List[SearchResult]:
        results = []
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=limit, region="jp-jp"))
        except Exception:
            try:
                with DDGS() as ddgs:
                    raw = list(ddgs.text(query, max_results=limit))
            except Exception:
                return []

        for i, item in enumerate(raw[:limit]):
            url = item.get("href", "")
            if not url:
                continue
            title = item.get("title", "")
            snippet = item.get("body", "")
            publisher = urlparse(url).netloc

            full_content = self._fetch_content(url)

            results.append(
                SearchResult(
                    url=url,
                    title=title,
                    publisher=publisher,
                    published_at=None,
                    snippet=snippet,
                    full_content=full_content,
                    source_type="article",
                    relevance_score=0.9 - (i * 0.05),
                )
            )
        return results

    def _fetch_content(self, url: str, max_chars: int = 3000) -> str:
        """Fetch and extract text from a URL. Returns empty string on failure."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            extracted = trafilatura.extract(resp.text, no_fallback=False)
            if extracted:
                return extracted[:max_chars]
        except Exception:
            pass
        return ""
