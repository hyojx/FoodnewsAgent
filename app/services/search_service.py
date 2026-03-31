"""Search service.

Uses Tavily Search API to search the web.
Full page content is returned directly by Tavily (include_raw_content=True),
so no separate fetch step is needed.
"""
import os
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from tavily import TavilyClient

# Domains that must never appear in food research results
_BLOCKED_DOMAINS: frozenset = frozenset({
    # Adult content
    "xvideos.com", "crot.media", "xnxx.com", "pornhub.com", "xhamster.com",
    "bokeptv.com",
    # App stores (not article content)
    "play.google.com", "apps.apple.com", "apps.microsoft.com",
    # Microsoft services (unrelated to food)
    "microsoft.com", "office.com", "account.microsoft.com", "support.microsoft.com",
    # Social media app pages
    "instagram.com", "facebook.com", "twitter.com", "tiktok.com",
    # Chinese video/entertainment
    "bilibili.com", "douban.com", "movie.douban.com", "baike.baidu.com",
    # Q&A / forum sites (low quality for research)
    "zhidao.baidu.com", "answers.yahoo.com", "quora.com",
    # Government / national park / non-food sites
    "nps.gov",
    # GIS / mapping services
    "tim-online.nrw.de", "openstreetmap.org", "maps.google.com",
    # Other clearly unrelated
    "absolutradio.de", "steam.work",
})


# Query templates per language × field_path
# Fallback for unknown field_path uses category as context (see _generate_queries).
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
    "zh": {
        "cases": ["{anchor} 案例 品牌", "{anchor} 企业 应用案例"],
        "trend_name": ["{anchor} 趋势 定义"],
        "definition": ["{anchor} 是什么 含义 定义"],
        "change_from_previous": ["{anchor} 变化 与以往比较"],
        "background": ["{anchor} 背景 历史"],
        "expansion_pattern.geographic_scope": ["{anchor} 全球扩展 地区"],
        "expansion_pattern.industry_expansion": ["{anchor} 行业 扩展"],
        "key_features": ["{anchor} 特点 功能"],
        "how_it_works": ["{anchor} 工作原理 方法"],
        "business_model.pricing": ["{anchor} 价格 收费"],
        "business_model.model": ["{anchor} 商业模式 收益"],
        "technology_principle": ["{anchor} 技术 原理 机制"],
        "applications": ["{anchor} 应用 企业 用途"],
        "results_and_effects": ["{anchor} 效果 结果 成效"],
        "industry_meaning": ["{anchor} 行业 意义 影响"],
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


def _is_blocked_domain(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return any(netloc == d or netloc.endswith("." + d) for d in _BLOCKED_DOMAINS)
    except Exception:
        return False


def _is_relevant(title: str, snippet: str, anchor: str) -> bool:
    """Check if a search result is relevant to the anchor keyword.

    Splits the anchor into significant tokens and checks if any appear in
    the result's title or snippet. Returns True when anchor is empty (no filter).
    Min token length is 2 to capture short but meaningful CJK/abbreviation terms.
    """
    if not anchor:
        return True
    text = (title + " " + snippet).lower()
    anchor_lower = anchor.lower()

    # Whole-anchor match first (works well for short product/company names)
    if anchor_lower in text:
        return True

    # Split by whitespace and common CJK/punctuation separators
    parts = re.split(r'[\s、。・,\[\]「」『』()（）/\-_]+', anchor)
    keywords = [p.strip().lower() for p in parts if len(p.strip()) >= 2]

    if not keywords:
        return True  # Cannot determine relevance — allow through

    return any(kw in text for kw in keywords)


class SearchService:
    def __init__(self):
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is not set")
        self._client = TavilyClient(api_key=api_key)

    def search(self, query: str, limit: int = 5, language: str = "en", anchor: str = "") -> List[SearchResult]:
        return self._execute_search(query, limit, language, anchor=anchor)

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
        # Strip array notation (e.g. "cases[0]" → "cases")
        base = field_path.split("[")[0]
        if base in templates:
            raw = templates[base]
        else:
            # Fallback: include category as context so queries aren't generic
            raw = [f"{anchor} {category} {field_path.replace('.', ' ')}"]
        return [t.format(anchor=anchor) for t in raw]

    def _execute_search(self, query: str, limit: int, language: str = "en", anchor: str = "") -> List[SearchResult]:
        try:
            response = self._client.search(
                query=query,
                max_results=min(limit * 2, 10),
                include_raw_content=True,
            )
            raw = response.get("results", [])
        except Exception:
            return []

        results = []
        for i, item in enumerate(raw):
            if len(results) >= limit:
                break

            url = item.get("url", "")
            if not url or _is_blocked_domain(url):
                continue

            title = item.get("title", "")
            snippet = item.get("content", "")

            if anchor and not _is_relevant(title, snippet, anchor):
                continue

            full_content = (item.get("raw_content") or "")[:3000]
            publisher = urlparse(url).netloc

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
                    relevance_score=item.get("score", 0.9 - (i * 0.05)),
                )
            )
        return results
