"""Extractor service.

Routes to LLM-based extraction (real) or stub extraction (for tests).
Use USE_STUB_EXTRACTOR=true env var to force stub mode in tests.
"""
import os
from typing import Any, Dict, List, Optional

from app.services.article_parser import ParsedArticle
from app.services.search_service import SearchResult
from app.models.category_schemas import get_empty_schema


_USE_STUB = os.environ.get("USE_STUB_EXTRACTOR", "").lower() in ("1", "true", "yes")


# ─── Stub extractor (used in tests) ─────────────────────────────────────────

def _make_vws(value: str, source_ids: List[str], notes: str = "") -> Dict:
    return {"value": value, "sources": source_ids, "notes": notes}


def _build_sources_master(
    article: ParsedArticle,
    search_results: List[SearchResult],
    existing_sources: Optional[List[Dict]] = None,
) -> List[Dict]:
    sources = list(existing_sources or [])
    existing_urls = {s["url"] for s in sources}

    if article.url not in existing_urls:
        next_id = f"S{len(sources) + 1}"
        sources.append({
            "source_id": next_id,
            "url": article.url,
            "title": article.title,
            "publisher": article.publisher,
            "published_at": article.published_at or "",
            "source_type": "article",
            "language": article.language,
            "relevance_score": 1.0,
            "is_duplicate": False,
        })
        existing_urls.add(article.url)

    for r in search_results:
        if r.url not in existing_urls:
            next_id = f"S{len(sources) + 1}"
            sources.append({
                "source_id": next_id,
                "url": r.url,
                "title": r.title,
                "publisher": r.publisher,
                "published_at": r.published_at or "",
                "source_type": r.source_type,
                "language": r.language,
                "relevance_score": r.relevance_score,
                "is_duplicate": False,
            })
            existing_urls.add(r.url)

    return sources


def _get_source_ids(sources: List[Dict], count: int = 2) -> List[str]:
    return [s["source_id"] for s in sources[:count]]


def _stub_extract(
    category: str,
    article: ParsedArticle,
    search_results: List[SearchResult],
    existing_schema: Optional[Dict] = None,
    researched_at: str = "",
) -> Dict:
    """Stub extractor — fills schema with dummy data. Used in tests."""
    schema = existing_schema or get_empty_schema(category)
    sources = _build_sources_master(article, search_results, schema.get("sources_master"))
    schema["sources_master"] = sources
    s_ids = _get_source_ids(sources)

    if not schema.get("topic") or not schema["topic"].strip():
        schema["topic"] = f"Stub Topic: {article.title[:60]}"
    if not schema.get("researched_at") or not schema["researched_at"].strip():
        schema["researched_at"] = researched_at or "2026-03-24"

    def _fill(path_parts, value):
        obj = schema
        for p in path_parts[:-1]:
            obj = obj.setdefault(p, {})
        last = path_parts[-1]
        if not isinstance(obj.get(last, {}), dict) or not obj.get(last, {}).get("value", "").strip():
            obj[last] = _make_vws(value, s_ids)

    if category == "해외 동향":
        _fill(["trend_name"], "Stub Trend Name")
        _fill(["definition"], "Stub definition.")
        _fill(["change_from_previous"], "Stub change.")
        if not schema.get("background"):
            schema["background"] = [_make_vws("Stub background.", s_ids)]
        cs = schema.setdefault("core_change_structure", {})
        if not cs.get("product_change", {}).get("value", "").strip():
            cs["product_change"] = _make_vws("Stub product change.", s_ids)
        if not cs.get("consumption_change", {}).get("value", "").strip():
            cs["consumption_change"] = _make_vws("Stub consumption change.", s_ids)
        if not schema.get("cases") or len(schema["cases"]) < 2:
            schema["cases"] = [
                {
                    "company": _make_vws(f"StubCompany{i+1}", s_ids),
                    "product_or_service": _make_vws(f"Stub Product {i+1}", s_ids),
                    "how_it_works": _make_vws(f"Stub how it works {i+1}.", s_ids),
                    "features": [_make_vws(f"Feature {i+1}.1", s_ids)],
                }
                for i in range(2)
            ]
        ep = schema.setdefault("expansion_pattern", {})
        if not ep.get("geographic_scope", {}).get("value", "").strip():
            ep["geographic_scope"] = _make_vws("Stub geographic scope.", s_ids)
        if not ep.get("industry_expansion", {}).get("value", "").strip():
            ep["industry_expansion"] = _make_vws("Stub industry expansion.", s_ids)

    elif category == "상품·서비스":
        _fill(["name"], "Stub Product Name")
        _fill(["summary"], "Stub product summary.")
        _fill(["developer", "company_name"], "StubDeveloper Inc.")
        _fill(["developer", "company_description"], "Stub company description.")
        _fill(["purpose"], "Stub product purpose.")
        _fill(["how_it_works"], "Stub how it works.")
        _fill(["business_model", "model"], "SaaS")
        _fill(["business_model", "pricing"], "비공개")
        _fill(["differentiation"], "Stub differentiation point.")
        if not schema.get("key_features") or len(schema["key_features"]) < 2:
            schema["key_features"] = [_make_vws(f"Stub feature {i+1}.", s_ids) for i in range(2)]
        if not schema.get("data_or_technology_basis"):
            schema["data_or_technology_basis"] = [_make_vws("Stub technology basis.", s_ids)]
        if not schema.get("use_effects"):
            schema["use_effects"] = [_make_vws("Stub use effect.", s_ids)]

    elif category == "푸드테크":
        _fill(["technology_name"], "Stub Technology Name")
        _fill(["summary"], "Stub technology summary.")
        _fill(["technology_principle"], "Stub technology principle.")
        _fill(["problem_with_existing_method"], "Stub existing problem.")
        _fill(["solution"], "Stub solution description.")
        _fill(["industry_meaning"], "Stub industry meaning.")
        if not schema.get("applications"):
            schema["applications"] = [{
                "company": _make_vws("StubFoodCo", s_ids),
                "application_form": _make_vws("Stub application form.", s_ids),
            }]
        if not schema.get("results_and_effects"):
            schema["results_and_effects"] = [_make_vws("Stub result effect.", s_ids)]
        if not schema.get("use_cases"):
            schema["use_cases"] = [_make_vws("Stub use case.", s_ids)]

    return schema


# ─── LLM extractor (real) ────────────────────────────────────────────────────

def _llm_extract_initial(
    category: str,
    article: ParsedArticle,
    search_results: List[SearchResult],
    existing_schema: Optional[Dict],
    researched_at: str,
) -> Dict:
    from app.services.llm_extractor import extract_initial
    empty = existing_schema or get_empty_schema(category)
    return extract_initial(category, article, empty, researched_at)


def _llm_extract_merge(
    category: str,
    article: ParsedArticle,
    search_results: List[SearchResult],
    existing_schema: Optional[Dict],
    researched_at: str,
) -> Dict:
    from app.services.llm_extractor import merge_sources
    schema = existing_schema or get_empty_schema(category)
    return merge_sources(category, schema, search_results, [])


# ─── Public API ───────────────────────────────────────────────────────────────

def extract(
    category: str,
    article: ParsedArticle,
    search_results: List[SearchResult],
    existing_schema: Optional[Dict] = None,
    researched_at: str = "",
    is_initial: bool = True,
) -> Dict:
    """Extract or merge schema. Delegates to stub or LLM based on env."""
    if _USE_STUB:
        return _stub_extract(category, article, search_results, existing_schema, researched_at)

    if is_initial:
        return _llm_extract_initial(category, article, search_results, existing_schema, researched_at)
    else:
        return _llm_extract_merge(category, article, search_results, existing_schema, researched_at)
