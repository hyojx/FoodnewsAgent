"""Prompts for the Outline Generator agent."""
import json
from typing import Any, Dict

from app.blog.templates.base import CategoryTemplate

SYSTEM_OUTLINE = """당신은 식품 산업 리서치 서비스의 블로그 구조 설계 전문가입니다.

역할: 정규화된 기사 JSON을 분석하여 블로그 글의 구조(아웃라인)만 생성합니다.

엄격한 규칙:
- JSON에 없는 내용을 절대 추가하지 마십시오.
- 문장을 쓰지 말고 구조(heading, points)만 작성합니다.
- points는 JSON 필드에서 추출한 핵심 키워드/사실만 포함합니다 (문장 X, bullet 수준 O).
- 섹션 수는 반드시 4~6개여야 합니다.
- 시사점은 반드시 마지막 섹션에만 위치합니다.
- 시사점의 points는 JSON 내 use_effects / industry_meaning / expansion_pattern 등 함의 관련 필드만 활용합니다.
- title은 상품명/기술명/트렌드명을 포함한 구체적인 명사구로 작성합니다.
- lead_angle은 1문장 이내로 핵심 사실만 서술합니다.
- evidence_map에는 각 섹션 인덱스(s1~s5)가 참조하는 JSON 필드명 목록을 기입합니다.
- 반드시 JSON으로만 응답합니다. 마크다운 없이 순수 JSON만 반환합니다.
- article_json에 implications_seed 필드가 있으면 시사점 섹션 points에 우선 반영합니다.
- article_json에 editor_hint 필드가 있으면 전체 아웃라인 구성 시 참고합니다.
- article_json에 exclude_topics 필드가 있으면 해당 주제는 아웃라인에서 제외합니다.

출력 스키마:
{
  "title": "string",
  "lead_angle": "string",
  "sections": [
    {"heading": "string", "points": ["string"]}
  ],
  "evidence_map": {
    "s1": ["field1", "field2"],
    "s2": ["field3"]
  }
}"""

# 지원하는 힌트 필드 및 역할 설명
HINT_FIELDS: Dict[str, str] = {
    "implications_seed": "시사점 섹션 points에 우선 반영",
    "editor_hint": "전체 아웃라인 구성 시 참고",
    "exclude_topics": "아웃라인에서 제외할 주제",
}


def _build_hints_block(article_json: Dict[str, Any]) -> str:
    """article_json에서 힌트 필드를 감지하여 프롬프트 블록을 생성한다."""
    hints = {k: article_json[k] for k in HINT_FIELDS if k in article_json}
    if not hints:
        return ""
    lines = "\n".join(f"- {k} ({HINT_FIELDS[k]}): {v}" for k, v in hints.items())
    return f"\n사용자 제공 힌트 (반드시 반영):\n{lines}\n"


def build_outline_prompt(
    article_json: Dict[str, Any],
    template: CategoryTemplate,
) -> str:
    hints_block = _build_hints_block(article_json)
    return f"""카테고리: {template.category}

섹션 템플릿 (반드시 이 순서와 제목 사용):
{json.dumps(template.sections, ensure_ascii=False)}

참조 evidence_map (섹션별 JSON 필드 매핑):
{json.dumps(template.evidence_map, ensure_ascii=False)}
{hints_block}
입력 JSON:
{json.dumps(article_json, ensure_ascii=False, indent=2)}

위 JSON의 내용만 활용하여 아웃라인을 생성합니다.
섹션 heading은 템플릿 이름을 그대로 사용하고, points는 해당 JSON 필드 값에서 추출합니다."""
