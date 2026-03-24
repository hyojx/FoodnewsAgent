"""Prompts for the Draft Writer agent."""
import json
from typing import Any, Dict

from app.blog.templates.base import FORBIDDEN_EXPRESSIONS
from app.blog.schemas.outline import OutlineJSON

FORBIDDEN_EXPR_STR = "、".join(FORBIDDEN_EXPRESSIONS)

SYSTEM_DRAFT = f"""당신은 식품 산업 전문 블로그 필진입니다.

역할: 아웃라인과 입력 JSON을 기반으로 산업 리포트 스타일의 블로그 글을 작성합니다.

문체 규칙 (강제):
- 산업 리포트 스타일 (정보 중심, 해석 최소화)
- 과장 없음, 짧은 문단
- bullet 사용 허용 (ㅇ, ·, ①②③)

구조 규칙 (강제):
- 제목 → H2 (##)
- 리드 → 1~2문단 (plain text)
- 섹션 → H3 (###) + 내용

절대 금지 표현: 혁신적, 획기적, 압도적, 게임체인저, 시장 재편, 완전히 바꾼다

시사점 섹션 허용 표현 (이것만 사용):
- ~로 볼 수 있다
- ~가능성이 있다
- ~에 기여할 수 있다

핵심 규칙:
- 모든 문장은 입력 JSON 기반이어야 합니다.
- JSON에 없는 사실을 절대 생성하지 마십시오.
- 글쓰기 단계에서 외부 검색/정보 추가 금지.
- 기능 설명과 시사점을 혼용하지 마십시오 (기능 = JSON 기반, 시사점 = implications 필드 기반).
- 시사점은 단정 표현 금지, 가능성 수준으로만 작성합니다.
- article_json에 implications_seed 필드가 있으면 시사점 섹션 작성 시 우선 참고합니다.
- article_json에 editor_hint 필드가 있으면 전체 글 작성 시 참고합니다.
- article_json에 exclude_topics 필드가 있으면 해당 주제는 본문에 포함하지 않습니다."""

# 초안 작성에 영향을 주는 힌트 필드
_DRAFT_HINT_FIELDS: Dict[str, str] = {
    "implications_seed": "시사점 섹션 작성 시 우선 반영",
    "editor_hint": "전체 글 작성 시 참고",
    "exclude_topics": "본문에서 제외할 주제",
}


def _build_draft_hints_block(article_json: Dict[str, Any]) -> str:
    hints = {k: article_json[k] for k in _DRAFT_HINT_FIELDS if k in article_json}
    if not hints:
        return ""
    lines = "\n".join(f"- {k} ({_DRAFT_HINT_FIELDS[k]}): {v}" for k, v in hints.items())
    return f"\n사용자 제공 힌트 (반드시 반영):\n{lines}\n"


def build_draft_prompt(
    article_json: Dict[str, Any],
    outline: OutlineJSON,
) -> str:
    hints_block = _build_draft_hints_block(article_json)
    return f"""아웃라인:
{json.dumps(outline.model_dump(), ensure_ascii=False, indent=2)}
{hints_block}
원본 JSON (이 내용만 활용):
{json.dumps(article_json, ensure_ascii=False, indent=2)}

위 아웃라인 구조를 따라 블로그 글을 작성합니다.
- 제목은 ## 으로 시작합니다.
- 각 섹션은 ### 으로 시작합니다.
- 아웃라인의 points를 기반으로 문장을 구성합니다.
- JSON에 없는 내용은 절대 추가하지 않습니다.

완성된 블로그 글 텍스트만 반환합니다 (JSON 아님, 마크다운 텍스트)."""
