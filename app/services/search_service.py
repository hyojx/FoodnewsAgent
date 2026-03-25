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
    "Accept-Language": "en,*;q=0.5",
}

# DuckDuckGo region codes per language
LANGUAGE_TO_REGION = {
    "ja": "jp-jp",
    "ko": "kr-kr",
    "zh": "zh-cn",
    "en": "wt-wt",
}

# Query templates per language
_QUERY_TEMPLATES: dict = {
    "ja": {
        "cases": ["{anchor} 事例 ブランド", "{anchor} 企業 活用事例"],
        "trend_name": ["{anchor} トレンド 定義"],
        "definition": ["{anchor} とは 意味 定義"],
        "change_from_previous": ["{anchor} 変化 従来比較"],
        "background": ["{anchor} 背景 歴史"],
        "expansion_pattern.geographic_scope": ["{anchor} グローバル展開 地域"],
        "expansion_pattern.industry_expansion": ["{anchor} 業界 拡大"],
        "key_features": ["{anchor} 特徴 機能"],
        "how_it_works": ["{anchor} 仕組み 方法"],
        "business_model.pricing": ["{anchor} 価格 料金"],
        "business_model.model": ["{anchor} ビジネスモデル 収益"],
        "technology_principle": ["{anchor} 技術 原理 仕組み"],
        "applications": ["{anchor} 応用 活用 企業"],
        "results_and_effects": ["{anchor} 効果 結果 実績"],
        "industry_meaning": ["{anchor} 業界 意義 影響"],
    },
    "en": {
        "cases": ["{anchor} case study brand", "{anchor} company use case example"],
        "trend_name": ["{anchor} trend definition"],
        "definition": ["{anchor} definition meaning overview"],
        "change_from_previous": ["{anchor} change comparison previous"],
        "background": ["{anchor} background history origin"],
        "expansion_pattern.geographic_scope": ["{anchor} global expansion region market"],
        "expansion_pattern.industry_expansion": ["{anchor} industry expansion sector"],
        "key_features": ["{anchor} features capabilities"],
        "how_it_works": ["{anchor} how it works mechanism"],
        "business_model.pricing": ["{anchor} pricing plans cost"],
        "business_model.model": ["{anchor} business model revenue"],
        "technology_principle": ["{anchor} technology principle mechanism"],
        "applications": ["{anchor} applications use cases companies"],
        "results_and_effects": ["{anchor} results effects outcomes"],
        "industry_meaning": ["{anchor} industry impact significance"],
    },
    "ko": {
        "cases": ["{anchor} 사례 브랜드", "{anchor} 기업 활용사례"],
        "trend_name": ["{anchor} 트렌드 정의"],
        "definition": ["{anchor} 이란 의미 정의"],
        "change_from_previous": ["{anchor} 변화 기존비교"],
        "background": ["{anchor} 배경 역사"],
        "expansion_pattern.geographic_scope": ["{anchor} 글로벌 확산 지역"],
        "expansion_pattern.industry_expansion": ["{anchor} 업계 확대"],
        "key_features": ["{anchor} 특징 기능"],
        "how_it_works": ["{anchor} 작동방식 방법"],
        "business_model.pricing": ["{anchor} 가격 요금"],
        "business_model.model": ["{anchor} 비즈니스모델 수익"],
        "technology_principle": ["{anchor} 기술 원리 메커니즘"],
        "applications": ["{anchor} 응용 활용 기업"],
        "results_and_effects": ["{anchor} 효과 결과 실적"],
        "industry_meaning": ["{anchor} 업계 의의 영향"],
    },
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
    language: str = "en"
    relevance_score: float = 0.8


class SearchService:
    def search(self, query: str, limit: int = 5, language: str = "en") -> List[SearchResult]:
        return self._execute_search(query, limit, language)

    def search_for_field(
        self,
        field_path: str,
        topic: str,
        category: str,
        article_title: str = "",
        limit: int = 3,
        language: str = "en",
    ) -> List[SearchResult]:
        queries = self._generate_queries(field_path, topic, category, article_title, language)
        results = []
        seen_urls = set()
        for q in queries[:2]:
            for r in self._execute_search(q, limit, language):
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    results.append(r)
        return results[:limit]

    def _generate_queries(
        self,
        field_path: str,
        topic: str,
        category: str,
        article_title: str = "",
        language: str = "en",
    ) -> List[str]:
        anchor = article_title.strip() if article_title.strip() else topic
        lang_key = language if language in _QUERY_TEMPLATES else "en"
        templates = _QUERY_TEMPLATES[lang_key]
        base = field_path.split("[")[0]
        raw = templates.get(base, [f"{anchor} {field_path.replace('.', ' ')}"])
        return [t.format(anchor=anchor) for t in raw]

    def _execute_search(self, query: str, limit: int, language: str = "en") -> List[SearchResult]:
        region = LANGUAGE_TO_REGION.get(language, "wt-wt")
        results = []
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=limit, region=region))
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
                    language=language,
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
