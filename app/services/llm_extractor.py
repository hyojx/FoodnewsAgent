"""LLM extractor using OpenAI GPT-4o.

Implements the 4 prompts from reference.md:
  A — Initial extraction from article
  C — Search query generation for missing fields
  D — Merge additional sources into existing schema
"""
import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.services.article_parser import ParsedArticle
from app.services.search_service import SearchResult

MODEL = "gpt-4o"
MAX_TOKENS = 16000

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key)
    return _client


# ─── Field guides per category ───────────────────────────────────────────────

FIELD_GUIDE = {
    "상품·서비스": """
FIELD GUIDE for 상품·서비스:
- topic: 연구 주제를 나타내는 짧은 키워드/태그. 기사 제목 요약이 아닌 주제어 (예: "AI 식품 트렌드 분석 서비스", "식물성 단백질 스낵")
- name: 상품 또는 서비스의 공식 명칭
- summary: 상품/서비스 전체를 2~3문장으로 요약
- developer.company_name: 개발·출시한 기업명
- developer.company_description: 개발사의 사업 분야 및 특징
- purpose: 이 상품/서비스가 해결하려는 문제 또는 제공 목적
- key_features: 상품의 차별화된 주요 기능 목록 (최소 2개, how_it_works와 중복 금지 — 기능의 이름/특성을 나열)
- how_it_works: 상품이 실제로 어떻게 동작하는지 메커니즘·프로세스 설명
- data_or_technology_basis: 상품이 기반하는 데이터셋, 학습 데이터, 핵심 기술, 알고리즘 (예: "10년치 해외 식품 트렌드 데이터 학습", "GPT 기반 생성 AI")
- business_model.pricing: 가격 정책 또는 요금 체계 (정보 없으면 "비공개")
- business_model.model: 수익 구조 (예: 구독형 SaaS, 라이선스, B2B 등)
- use_effects: 이 상품/서비스가 업계 전반에 미치는 영향·파급 효과 (개별 사용자 효과가 아닌 산업적 관점, 예: "식품 기업의 트렌드 조사 방식 변화", "중소 식품 브랜드의 해외 시장 진입 장벽 완화")
- differentiation: 기존 유사 상품·서비스 대비 차별화 포인트
""",
    "해외 동향": """
FIELD GUIDE for 해외 동향:
- topic: 연구 주제를 나타내는 짧은 키워드/태그 (예: "북미 발효식품 트렌드", "유럽 대체육 시장 성장")
- trend_name: 트렌드의 공식·통용 명칭
- definition: 해당 트렌드가 무엇인지 정의
- change_from_previous: 이전 트렌드 또는 기존 시장 대비 달라진 점
- background: 이 트렌드가 등장하게 된 배경 요인들 (복수 가능)
- core_change_structure.product_change: 트렌드로 인해 제품 측면에서 일어나는 변화
- core_change_structure.consumption_change: 트렌드로 인해 소비자 행동·소비 방식에서 일어나는 변화
- cases[].company: 트렌드를 실제로 구현한 기업명
- cases[].product_or_service: 해당 기업의 구체적인 제품 또는 서비스명
- cases[].how_it_works: 해당 사례가 트렌드를 어떻게 구현했는지 설명
- cases[].features: 해당 사례의 특징적인 요소들
- expansion_pattern.geographic_scope: 트렌드가 확산되고 있는 지역·국가 범위
- expansion_pattern.industry_expansion: 트렌드가 식품 외 다른 산업으로 확장되는 양상
""",
    "푸드테크": """
FIELD GUIDE for 푸드테크:
- topic: 연구 주제를 나타내는 짧은 키워드/태그 (예: "AI 품질 검사 자동화", "정밀발효 단백질")
- technology_name: 기술의 공식·통용 명칭
- summary: 기술 전체를 2~3문장으로 요약
- technology_principle: 기술이 작동하는 원리 (과학적·공학적 메커니즘)
- problem_with_existing_method: 이 기술이 등장하기 전 기존 방식의 문제점·한계
- solution: 이 기술이 기존 문제를 어떻게 해결하는지
- applications[].company: 이 기술을 실제 적용한 기업명
- applications[].application_form: 해당 기업이 기술을 어떤 형태로 적용했는지 (제품명, 공정 등)
- results_and_effects: 기술 적용으로 나타난 수치·성과·효과 (예: "불량률 30% 감소", "생산 비용 20% 절감")
- use_cases: 기술이 활용되는 상황·맥락·적용 분야 (results_and_effects와 구분 — 성과 수치가 아닌 활용 상황 서술)
- industry_meaning: 이 기술이 식품 산업 전반에 갖는 의미·영향
""",
}


def _get_field_guide(category: str) -> str:
    return FIELD_GUIDE.get(category, "")


# ─── Prompt A: Initial extraction ────────────────────────────────────────────

SYSTEM_EXTRACTOR = """You are a structured research extraction engine for a food industry research service.

Your task is to fill a target JSON schema using ONLY the provided source documents.

STRICT RULES:
- Do NOT infer or fabricate values not supported by the sources.
- Every non-empty field value MUST reference one or more valid source_ids from sources_master.
- If evidence is insufficient, leave the field value as empty string "".
- Preserve the exact schema structure — do not add or remove keys.
- For array fields, add items only when you have evidence. Minimum item counts are goals, not obligations.
- Return ONLY valid JSON — no markdown, no explanation.
- IMPORTANT: All field values MUST be written in Korean (한국어), regardless of the source language.
  Translate Japanese, English, or any other language content into natural Korean.
"""

def extract_initial(
    category: str,
    article: ParsedArticle,
    empty_schema: Dict,
    researched_at: str,
) -> Dict:
    """Prompt A: Fill schema from original article only."""
    client = get_client()

    sources_master = [
        {
            "source_id": "S1",
            "url": article.url,
            "title": article.title,
            "publisher": article.publisher,
            "published_at": article.published_at or "",
            "source_type": "article",
            "language": article.language,
            "relevance_score": 1.0,
            "is_duplicate": False,
        }
    ]

    schema_to_fill = dict(empty_schema)
    schema_to_fill["sources_master"] = sources_master
    schema_to_fill["category"] = category
    schema_to_fill["researched_at"] = researched_at

    field_guide = _get_field_guide(category)

    prompt = f"""Category: {category}
{field_guide}
Source documents:
[S1] {article.title}
URL: {article.url}
---
{article.cleaned_content[:6000]}

Target schema to fill:
{json.dumps(schema_to_fill, ensure_ascii=False, indent=2)}

Fill the schema using ONLY the content above. Return the filled JSON."""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_EXTRACTOR},
            {"role": "user", "content": prompt},
        ],
    )

    text = response.choices[0].message.content or ""
    return _parse_json_response(text, schema_to_fill)


# ─── Prompt D: Merge new sources ─────────────────────────────────────────────

SYSTEM_MERGER = """You are a structured evidence merger for a food industry research service.

Your task is to update a partially filled JSON schema by incorporating new source documents.

STRICT RULES:
- Only update fields when new sources provide stronger or additional evidence.
- Keep prior valid values unless contradicted by higher-quality evidence.
- If sources conflict, preserve a cautious merged statement and add to "notes".
- Every non-empty field value MUST reference valid source_ids from sources_master.
- New sources are already added to sources_master — use their source_ids.
- Do NOT fabricate values. If new sources don't help a field, leave it as-is.
- Return ONLY valid JSON — no markdown, no explanation.
- IMPORTANT: All field values MUST be written in Korean (한국어), regardless of the source language.
  Translate Japanese, English, or any other language content into natural Korean.
"""

def merge_sources(
    category: str,
    current_schema: Dict,
    new_results: List[SearchResult],
    missing_fields: List[str],
) -> Dict:
    """Prompt D: Merge new search results into existing schema."""
    if not new_results:
        return current_schema

    client = get_client()

    existing_urls = {s["url"] for s in current_schema.get("sources_master", [])}
    updated_sources = list(current_schema.get("sources_master", []))

    for r in new_results:
        if r.url not in existing_urls and r.full_content:
            next_id = f"S{len(updated_sources) + 1}"
            updated_sources.append({
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

    updated_schema = dict(current_schema)
    updated_schema["sources_master"] = updated_sources

    source_blocks = []
    for s in updated_sources:
        content = next(
            (r.full_content or r.snippet for r in new_results if r.url == s["url"]),
            ""
        )
        if content:
            source_blocks.append(
                f"[{s['source_id']}] {s['title']}\nURL: {s['url']}\n---\n{content[:2000]}"
            )

    if not source_blocks:
        return current_schema

    sources_text = "\n\n".join(source_blocks[:5])

    field_guide = _get_field_guide(category)

    prompt = f"""Category: {category}
{field_guide}
Missing fields to focus on: {json.dumps(missing_fields, ensure_ascii=False)}

New source documents:
{sources_text}

Current schema (merge new evidence into this):
{json.dumps(updated_schema, ensure_ascii=False, indent=2)}

Update the schema with evidence from the new sources. Return the complete updated JSON."""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_MERGER},
            {"role": "user", "content": prompt},
        ],
    )

    text = response.choices[0].message.content or ""
    return _parse_json_response(text, updated_schema)


# ─── Prompt C: Search query generation ───────────────────────────────────────

_LANG_NAMES = {"ja": "Japanese", "ko": "Korean", "en": "English", "zh": "Chinese"}

SYSTEM_QUERY_GEN = """You are a research query generator for a food industry research service.

Generate targeted web search queries to fill missing fields in a research schema.
Use the article's language for better search coverage.
Return ONLY a JSON object: {"queries": [...]}"""

def generate_search_queries(
    category: str,
    topic: str,
    article_title: str,
    missing_fields: List[str],
    limit_per_field: int = 2,
    article_language: str = "en",
) -> List[str]:
    """Prompt C: Generate search queries for missing fields."""
    client = get_client()
    lang_name = _LANG_NAMES.get(article_language, "English")

    prompt = f"""Category: {category}
Topic: {topic}
Article title: {article_title}
Article language: {lang_name}
Missing fields: {json.dumps(missing_fields[:8], ensure_ascii=False)}

Generate up to {limit_per_field} targeted search queries per missing field.
IMPORTANT: Each query MUST include the article title or topic keyword as anchor — do NOT generate generic queries without it.
Use {lang_name} for the queries (match the article's language).
Return: {{"queries": [...]}}"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=2000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_QUERY_GEN},
            {"role": "user", "content": prompt},
        ],
    )

    text = response.choices[0].message.content or "{}"
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(q) for q in data]
        if isinstance(data, dict):
            for key in ("queries", "search_queries", "results"):
                if key in data and isinstance(data[key], list):
                    return [str(q) for q in data[key]]
    except Exception:
        pass
    return []


# ─── Prompt E: Additional research query generation ───────────────────────────

SYSTEM_ADDITIONAL_QUERY_GEN = """You are a research query generator for a food industry research service.

A user has an existing research document and wants to find additional specific information.
Their request is written in Korean. Generate targeted web search queries to find what they need.
Return ONLY a JSON object: {"queries": [...]}"""


def generate_additional_queries(
    filled_schema: Dict,
    additional_query: str,
    article_language: str = "en",
) -> List[str]:
    """Generate search queries from a natural language additional research request."""
    client = get_client()
    lang_name = _LANG_NAMES.get(article_language, "English")

    sources = filled_schema.get("sources_master", [])
    original_source = sources[0] if sources else {}
    topic = filled_schema.get("topic", "")
    category = filled_schema.get("category", "")

    prompt = f"""Existing research context:
- Category: {category}
- Topic: {topic}
- Original article: {original_source.get("title", "")}

User's additional research request (in Korean):
{additional_query}

Generate 4-6 targeted web search queries to find the requested information.
Use {lang_name} for the queries (match the original article's language).
Each query must be specific and include the topic/product name as anchor.
Return: {{"queries": [...]}}"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_ADDITIONAL_QUERY_GEN},
            {"role": "user", "content": prompt},
        ],
    )

    text = response.choices[0].message.content or "{}"
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(q) for q in data]
        if isinstance(data, dict):
            for key in ("queries", "search_queries", "results"):
                if key in data and isinstance(data[key], list):
                    return [str(q) for q in data[key]]
    except Exception:
        pass
    return []


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_json_response(text: str, fallback: Dict) -> Dict:
    """Parse JSON from response text, falling back to existing schema on error."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        inner = lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()

    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
    return fallback
