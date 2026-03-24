"""Tests for the blog pipeline module (app/blog/).

Coverage:
  - schemas: ArticleInput, OutlineJSON, ReviewResult, PipelineStatus
  - templates: all 3 categories
  - prompts: prompt builders
  - pipeline agents: OutlineGenerator, DraftWriter, ReviewAgent (LLM mocked)
  - pipeline orchestrator: BlogPipeline with status tracking
  - API endpoints: /generate-outline, /generate-draft, /review-draft, /generate-post
"""
import json
import pytest
from unittest.mock import MagicMock, patch

# ─── Shared fixtures ──────────────────────────────────────────────────────────

SAMPLE_PRODUCT_JSON = {
    "category": "상품·서비스",
    "topic": "AI 식품 트렌드 분석 서비스",
    "researched_at": "2026-03-24",
    "sources_master": [
        {
            "source_id": "S1",
            "url": "https://example.com/article",
            "title": "FOODIAL AI 출시",
            "publisher": "PR TIMES",
            "published_at": "2026-02-25",
        }
    ],
    "name": {"value": "FOODIAL AI", "sources": ["S1"]},
    "summary": {
        "value": "FOODIAL AI는 10년간의 식품 트렌드를 학습한 식품 특화 AI 서비스입니다.",
        "sources": ["S1"],
    },
    "developer": {
        "company_name": {"value": "株式会社TNC", "sources": ["S1"]},
        "company_description": {"value": "TNC는 해외 식품 마케팅 전문 기업입니다.", "sources": ["S1"]},
    },
    "purpose": {
        "value": "해외 식품 트렌드 기반 상품 개발 및 마케팅 전략 지원",
        "sources": ["S1"],
    },
    "key_features": [
        {"description": "10년치 식품 트렌드 횡단 검색 기능", "sources": ["S1"]},
        {"description": "마케팅 시각 반영한 아이디어 발상 지원", "sources": ["S1"]},
    ],
    "how_it_works": {
        "value": "TNC 1차 정보 기반으로 정확한 근거를 바탕으로 정보를 제공합니다.",
        "sources": ["S1"],
    },
    "data_or_technology_basis": [
        {"description": "10년치 해외 식품 트렌드 리포트 학습 데이터", "sources": ["S1"]}
    ],
    "business_model": {
        "pricing": {"value": "비공개", "sources": ["S1"]},
        "model": {"value": "B2B 유료 구독형", "sources": ["S1"]},
    },
    "use_effects": [
        {"description": "식품 기업의 트렌드 조사 방식 효율화 가능성", "sources": ["S1"]}
    ],
    "differentiation": {
        "value": "산업 특화 1차 데이터 기반으로 일반 생성AI 대비 구체성 있는 응답 제공",
        "sources": ["S1"],
    },
}

SAMPLE_FOODTECH_JSON = {
    "category": "푸드테크",
    "topic": "AI 품질 검사 자동화",
    "researched_at": "2026-03-24",
    "sources_master": [{"source_id": "S1", "url": "https://example.com", "title": "Test"}],
    "technology_name": {"value": "AI 비전 품질 검사", "sources": ["S1"]},
    "summary": {"value": "AI 카메라로 식품 불량을 자동 검출하는 기술", "sources": ["S1"]},
    "technology_principle": {"value": "딥러닝 기반 이미지 분류", "sources": ["S1"]},
    "problem_with_existing_method": {"value": "사람 육안 검사의 불일치 문제", "sources": ["S1"]},
    "solution": {"value": "AI가 24시간 일정 기준으로 검사", "sources": ["S1"]},
    "applications": [
        {
            "company": {"value": "ABCFood", "sources": ["S1"]},
            "application_form": {"value": "생산라인 카메라 설치", "sources": ["S1"]},
        }
    ],
    "results_and_effects": [{"description": "불량률 30% 감소", "sources": ["S1"]}],
    "use_cases": [{"description": "육가공 라인 품질 검사", "sources": ["S1"]}],
    "industry_meaning": {"value": "식품 품질 자동화의 사례로 볼 수 있다", "sources": ["S1"]},
}

SAMPLE_TREND_JSON = {
    "category": "해외 동향",
    "topic": "북미 발효식품 트렌드",
    "researched_at": "2026-03-24",
    "sources_master": [{"source_id": "S1", "url": "https://example.com", "title": "Test"}],
    "trend_name": {"value": "프리미엄 발효식품 트렌드", "sources": ["S1"]},
    "definition": {"value": "고급 발효 음료 및 식품 수요 증가", "sources": ["S1"]},
    "change_from_previous": {"value": "일반 유통채널에서 프리미엄 채널로 이동", "sources": ["S1"]},
    "background": [{"description": "건강 의식 소비자 증가", "sources": ["S1"]}],
    "core_change_structure": {
        "product_change": {"value": "고급 원재료 사용 증가", "sources": ["S1"]},
        "consumption_change": {"value": "소량 구매 고빈도 소비", "sources": ["S1"]},
    },
    "cases": [
        {
            "company": {"value": "BrandX", "sources": ["S1"]},
            "product_or_service": {"value": "콤부차 프리미엄", "sources": ["S1"]},
            "how_it_works": {"value": "유기농 원재료 발효", "sources": ["S1"]},
            "features": [{"description": "천연 발효 공정", "sources": ["S1"]}],
        },
        {
            "company": {"value": "BrandY", "sources": ["S1"]},
            "product_or_service": {"value": "케피어 음료", "sources": ["S1"]},
            "how_it_works": {"value": "저온 발효 공정", "sources": ["S1"]},
            "features": [{"description": "프로바이오틱스 강화", "sources": ["S1"]}],
        },
    ],
    "expansion_pattern": {
        "geographic_scope": {"value": "북미 → 유럽으로 확산", "sources": ["S1"]},
        "industry_expansion": {"value": "식음료 외 뷰티 산업으로 확장 가능성", "sources": ["S1"]},
    },
}

SAMPLE_OUTLINE = {
    "title": "10년치 해외 식품 데이터 기반 AI 'FOODIAL AI' 출시",
    "lead_angle": "일본 TNC가 식품 트렌드 데이터 기반 AI 서비스를 선보였다.",
    "sections": [
        {"heading": "서비스 개요", "points": ["FOODIAL AI", "TNC 개발"]},
        {"heading": "개발 배경 / 해결 문제", "points": ["해외 정보 탐색 어려움"]},
        {"heading": "핵심 기능", "points": ["횡단 검색", "아이디어 지원"]},
        {"heading": "이용 방식 / 도입 방식", "points": ["B2B 유료 구독"]},
        {"heading": "시사점", "points": ["산업 특화 AI 사례", "효율화 가능성"]},
    ],
    "evidence_map": {
        "s1": ["name", "summary"],
        "s2": ["purpose"],
        "s3": ["key_features"],
        "s4": ["business_model.model"],
        "s5": ["use_effects"],
    },
}

SAMPLE_DRAFT = """## 10년치 해외 식품 데이터 기반 AI 'FOODIAL AI' 출시

일본 TNC가 식품 트렌드 데이터 기반 AI 서비스를 선보였다.

### 1. 서비스 개요
ㅇ FOODIAL AI는 10년 식품 트렌드를 학습한 AI 서비스다.

### 2. 개발 배경 / 해결 문제
ㅇ 해외 식품 정보 탐색이 어렵다.

### 3. 핵심 기능
ㅇ 10년치 트렌드 횡단 검색 기능을 제공한다.

### 4. 이용 방식 / 도입 방식
ㅇ B2B 유료 구독형으로 제공된다.

### 5. 시사점
ㅇ 산업 특화 데이터 기반 AI 사례로 볼 수 있다.
ㅇ 식품 기업 트렌드 조사 효율화에 기여할 가능성이 있다.
"""


def _llm_response(content: str) -> MagicMock:
    """Build a minimal mock OpenAI response."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ─── Schema tests ─────────────────────────────────────────────────────────────

class TestArticleInput:
    def test_valid_product_category(self):
        from app.blog.schemas.article import ArticleInput
        obj = ArticleInput(article_json=SAMPLE_PRODUCT_JSON)
        assert obj.article_json["category"] == "상품·서비스"

    def test_valid_foodtech_category(self):
        from app.blog.schemas.article import ArticleInput
        obj = ArticleInput(article_json=SAMPLE_FOODTECH_JSON)
        assert obj.article_json["category"] == "푸드테크"

    def test_valid_trend_category(self):
        from app.blog.schemas.article import ArticleInput
        obj = ArticleInput(article_json=SAMPLE_TREND_JSON)
        assert obj.article_json["category"] == "해외 동향"

    def test_invalid_category_raises(self):
        from app.blog.schemas.article import ArticleInput
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ArticleInput(article_json={"category": "unknown"})

    def test_empty_json_raises(self):
        from app.blog.schemas.article import ArticleInput
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ArticleInput(article_json={})


class TestOutlineJSON:
    def test_valid_outline(self):
        from app.blog.schemas.outline import OutlineJSON, OutlineSection
        outline = OutlineJSON(
            title="Test",
            lead_angle="Lead",
            sections=[
                OutlineSection(heading=f"H{i}", points=["p"])
                for i in range(5)
            ],
        )
        assert len(outline.sections) == 5

    def test_too_few_sections_raises(self):
        from app.blog.schemas.outline import OutlineJSON, OutlineSection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OutlineJSON(
                title="T",
                lead_angle="L",
                sections=[OutlineSection(heading="H1", points=[])],
            )

    def test_too_many_sections_raises(self):
        from app.blog.schemas.outline import OutlineJSON, OutlineSection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OutlineJSON(
                title="T",
                lead_angle="L",
                sections=[
                    OutlineSection(heading=f"H{i}", points=[]) for i in range(7)
                ],
            )

    def test_exactly_4_sections_ok(self):
        from app.blog.schemas.outline import OutlineJSON, OutlineSection
        outline = OutlineJSON(
            title="T",
            lead_angle="L",
            sections=[OutlineSection(heading=f"H{i}", points=[]) for i in range(4)],
        )
        assert len(outline.sections) == 4

    def test_exactly_6_sections_ok(self):
        from app.blog.schemas.outline import OutlineJSON, OutlineSection
        outline = OutlineJSON(
            title="T",
            lead_angle="L",
            sections=[OutlineSection(heading=f"H{i}", points=[]) for i in range(6)],
        )
        assert len(outline.sections) == 6

    def test_evidence_map_default_empty(self):
        from app.blog.schemas.outline import OutlineJSON, OutlineSection
        outline = OutlineJSON(
            title="T",
            lead_angle="L",
            sections=[OutlineSection(heading=f"H{i}", points=[]) for i in range(4)],
        )
        assert outline.evidence_map == {}


class TestPipelineStatus:
    def test_all_seven_statuses_defined(self):
        from app.blog.schemas.review import PipelineStatus
        expected = {
            "EXTRACTED", "NORMALIZED", "OUTLINE_CREATED",
            "DRAFT_CREATED", "REVIEW_FAILED", "REVIEW_PASSED", "FINALIZED",
        }
        actual = {s.value for s in PipelineStatus}
        assert actual == expected


class TestReviewResult:
    def test_build_review_result(self):
        from app.blog.schemas.review import ReviewResult, ReviewIssue
        result = ReviewResult(
            passed=True,
            issues=[],
            revised_draft="draft text",
        )
        assert result.passed is True
        assert result.revised_draft == "draft text"

    def test_review_issue_fields(self):
        from app.blog.schemas.review import ReviewIssue
        issue = ReviewIssue(type="forbidden_expression", text="혁신적", reason="금지 표현")
        assert issue.type == "forbidden_expression"
        assert issue.text == "혁신적"


# ─── Template tests ───────────────────────────────────────────────────────────

class TestTemplates:
    def test_all_three_templates_exist(self):
        from app.blog.templates import CATEGORY_TEMPLATES
        assert "상품·서비스" in CATEGORY_TEMPLATES
        assert "푸드테크" in CATEGORY_TEMPLATES
        assert "해외 동향" in CATEGORY_TEMPLATES

    def test_product_template_has_5_sections(self):
        from app.blog.templates.product import PRODUCT_TEMPLATE
        assert len(PRODUCT_TEMPLATE.sections) == 5
        assert "시사점" in PRODUCT_TEMPLATE.sections

    def test_foodtech_template_has_5_sections(self):
        from app.blog.templates.foodtech import FOODTECH_TEMPLATE
        assert len(FOODTECH_TEMPLATE.sections) == 5
        assert "시사점" in FOODTECH_TEMPLATE.sections

    def test_trend_template_has_5_sections(self):
        from app.blog.templates.trend import TREND_TEMPLATE
        assert len(TREND_TEMPLATE.sections) == 5
        assert any("시사점" in s for s in TREND_TEMPLATE.sections)

    def test_implication_section_is_last(self):
        from app.blog.templates import CATEGORY_TEMPLATES
        for cat, tmpl in CATEGORY_TEMPLATES.items():
            last = tmpl.sections[-1]
            assert "시사점" in last, f"{cat} last section must contain '시사점'"

    def test_evidence_map_keys_match_section_count(self):
        from app.blog.templates import CATEGORY_TEMPLATES
        for cat, tmpl in CATEGORY_TEMPLATES.items():
            assert len(tmpl.evidence_map) == len(tmpl.sections), (
                f"{cat} evidence_map size mismatch"
            )

    def test_get_template_returns_correct(self):
        from app.blog.templates import get_template
        t = get_template("상품·서비스")
        assert t.category == "상품·서비스"

    def test_get_template_unknown_raises(self):
        from app.blog.templates import get_template
        with pytest.raises(ValueError):
            get_template("존재하지않는카테고리")

    def test_forbidden_expressions_list(self):
        from app.blog.templates.base import FORBIDDEN_EXPRESSIONS
        assert len(FORBIDDEN_EXPRESSIONS) >= 5
        assert "혁신적" in FORBIDDEN_EXPRESSIONS
        assert "시장 재편" in FORBIDDEN_EXPRESSIONS


# ─── Prompt tests ─────────────────────────────────────────────────────────────

class TestPrompts:
    def test_build_outline_prompt_contains_category(self):
        from app.blog.prompts.outline import build_outline_prompt
        from app.blog.templates.product import PRODUCT_TEMPLATE
        prompt = build_outline_prompt(SAMPLE_PRODUCT_JSON, PRODUCT_TEMPLATE)
        assert "상품·서비스" in prompt

    def test_build_outline_prompt_contains_sections(self):
        from app.blog.prompts.outline import build_outline_prompt
        from app.blog.templates.product import PRODUCT_TEMPLATE
        prompt = build_outline_prompt(SAMPLE_PRODUCT_JSON, PRODUCT_TEMPLATE)
        assert "서비스 개요" in prompt
        assert "시사점" in prompt

    def test_build_draft_prompt_contains_forbidden_warning(self):
        from app.blog.prompts.draft import SYSTEM_DRAFT
        assert "혁신적" in SYSTEM_DRAFT or "금지" in SYSTEM_DRAFT

    def test_build_draft_prompt_contains_outline(self):
        from app.blog.prompts.draft import build_draft_prompt
        from app.blog.schemas.outline import OutlineJSON, OutlineSection
        outline = OutlineJSON(**SAMPLE_OUTLINE)
        prompt = build_draft_prompt(SAMPLE_PRODUCT_JSON, outline)
        assert "서비스 개요" in prompt

    def test_build_review_prompt_contains_forbidden_list(self):
        from app.blog.prompts.review import build_review_prompt
        from app.blog.schemas.outline import OutlineJSON
        outline = OutlineJSON(**SAMPLE_OUTLINE)
        prompt = build_review_prompt(SAMPLE_PRODUCT_JSON, outline, SAMPLE_DRAFT)
        assert "혁신적" in prompt

    def test_system_review_contains_all_issue_types(self):
        from app.blog.prompts.review import SYSTEM_REVIEW
        assert "unsupported_claim" in SYSTEM_REVIEW
        assert "forbidden_expression" in SYSTEM_REVIEW
        assert "missing_section" in SYSTEM_REVIEW
        assert "definitive_implication" in SYSTEM_REVIEW

    # ── 힌트 필드 반영 테스트 ──────────────────────────────────────────────────

    def test_outline_prompt_includes_implications_seed(self):
        from app.blog.prompts.outline import build_outline_prompt
        from app.blog.templates.product import PRODUCT_TEMPLATE
        article_with_hint = {**SAMPLE_PRODUCT_JSON, "implications_seed": "B2C 확장 가능성"}
        prompt = build_outline_prompt(article_with_hint, PRODUCT_TEMPLATE)
        assert "implications_seed" in prompt
        assert "B2C 확장 가능성" in prompt
        assert "사용자 제공 힌트" in prompt

    def test_outline_prompt_no_hints_block_when_no_hint_fields(self):
        from app.blog.prompts.outline import build_outline_prompt
        from app.blog.templates.product import PRODUCT_TEMPLATE
        prompt = build_outline_prompt(SAMPLE_PRODUCT_JSON, PRODUCT_TEMPLATE)
        assert "사용자 제공 힌트" not in prompt

    def test_outline_prompt_includes_editor_hint(self):
        from app.blog.prompts.outline import build_outline_prompt
        from app.blog.templates.product import PRODUCT_TEMPLATE
        article_with_hint = {**SAMPLE_PRODUCT_JSON, "editor_hint": "B2C 사례 제외 요망"}
        prompt = build_outline_prompt(article_with_hint, PRODUCT_TEMPLATE)
        assert "editor_hint" in prompt
        assert "B2C 사례 제외 요망" in prompt

    def test_outline_prompt_includes_exclude_topics(self):
        from app.blog.prompts.outline import build_outline_prompt
        from app.blog.templates.product import PRODUCT_TEMPLATE
        article_with_hint = {**SAMPLE_PRODUCT_JSON, "exclude_topics": "가격 정책"}
        prompt = build_outline_prompt(article_with_hint, PRODUCT_TEMPLATE)
        assert "exclude_topics" in prompt
        assert "가격 정책" in prompt

    def test_outline_prompt_multiple_hints(self):
        from app.blog.prompts.outline import build_outline_prompt
        from app.blog.templates.product import PRODUCT_TEMPLATE
        article_with_hints = {
            **SAMPLE_PRODUCT_JSON,
            "implications_seed": "데이터 기반 의사결정 확산",
            "editor_hint": "기술적 세부사항 최소화",
        }
        prompt = build_outline_prompt(article_with_hints, PRODUCT_TEMPLATE)
        assert "데이터 기반 의사결정 확산" in prompt
        assert "기술적 세부사항 최소화" in prompt

    def test_draft_prompt_includes_implications_seed(self):
        from app.blog.prompts.draft import build_draft_prompt
        from app.blog.schemas.outline import OutlineJSON
        article_with_hint = {**SAMPLE_PRODUCT_JSON, "implications_seed": "중소기업 활용 가능성"}
        outline = OutlineJSON(**SAMPLE_OUTLINE)
        prompt = build_draft_prompt(article_with_hint, outline)
        assert "implications_seed" in prompt
        assert "중소기업 활용 가능성" in prompt
        assert "사용자 제공 힌트" in prompt

    def test_draft_prompt_no_hints_block_when_no_hint_fields(self):
        from app.blog.prompts.draft import build_draft_prompt
        from app.blog.schemas.outline import OutlineJSON
        outline = OutlineJSON(**SAMPLE_OUTLINE)
        prompt = build_draft_prompt(SAMPLE_PRODUCT_JSON, outline)
        assert "사용자 제공 힌트" not in prompt

    def test_system_outline_mentions_hint_fields(self):
        from app.blog.prompts.outline import SYSTEM_OUTLINE
        assert "implications_seed" in SYSTEM_OUTLINE
        assert "editor_hint" in SYSTEM_OUTLINE
        assert "exclude_topics" in SYSTEM_OUTLINE

    def test_system_draft_mentions_hint_fields(self):
        from app.blog.prompts.draft import SYSTEM_DRAFT
        assert "implications_seed" in SYSTEM_DRAFT
        assert "editor_hint" in SYSTEM_DRAFT
        assert "exclude_topics" in SYSTEM_DRAFT


# ─── Agent unit tests ─────────────────────────────────────────────────────────

class TestOutlineGenerator:
    def test_generate_returns_outline_json(self):
        from app.blog.pipeline.generate import OutlineGenerator
        from app.blog.schemas.outline import OutlineJSON

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response(
            json.dumps(SAMPLE_OUTLINE)
        )

        with patch("app.blog.pipeline.generate.get_llm_client", return_value=mock_client):
            gen = OutlineGenerator()
            result = gen.generate(SAMPLE_PRODUCT_JSON)

        assert isinstance(result, OutlineJSON)
        assert result.title == SAMPLE_OUTLINE["title"]
        assert 4 <= len(result.sections) <= 6

    def test_generate_falls_back_on_invalid_json(self):
        from app.blog.pipeline.generate import OutlineGenerator
        from app.blog.schemas.outline import OutlineJSON

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response("not json {{{{")

        with patch("app.blog.pipeline.generate.get_llm_client", return_value=mock_client):
            gen = OutlineGenerator()
            result = gen.generate(SAMPLE_PRODUCT_JSON)

        assert isinstance(result, OutlineJSON)
        # Fallback builds from template → 5 sections
        assert 4 <= len(result.sections) <= 6

    def test_generate_pads_sections_if_too_few(self):
        from app.blog.pipeline.generate import OutlineGenerator

        sparse = {
            "title": "Test",
            "lead_angle": "Lead",
            "sections": [
                {"heading": "서비스 개요", "points": ["a"]},
                {"heading": "핵심 기능", "points": ["b"]},
            ],
            "evidence_map": {},
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response(json.dumps(sparse))

        with patch("app.blog.pipeline.generate.get_llm_client", return_value=mock_client):
            gen = OutlineGenerator()
            result = gen.generate(SAMPLE_PRODUCT_JSON)

        assert len(result.sections) >= 4

    def test_generate_uses_category_template(self):
        from app.blog.pipeline.generate import OutlineGenerator

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response(
            json.dumps(SAMPLE_OUTLINE)
        )

        with patch("app.blog.pipeline.generate.get_llm_client", return_value=mock_client):
            gen = OutlineGenerator()
            result = gen.generate(SAMPLE_PRODUCT_JSON)

        headings = [s.heading for s in result.sections]
        assert any("서비스 개요" in h or "개요" in h for h in headings)


class TestDraftWriter:
    def test_write_returns_string(self):
        from app.blog.pipeline.generate import DraftWriter
        from app.blog.schemas.outline import OutlineJSON

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response(SAMPLE_DRAFT)

        with patch("app.blog.pipeline.generate.get_llm_client", return_value=mock_client):
            writer = DraftWriter()
            result = writer.write(SAMPLE_PRODUCT_JSON, OutlineJSON(**SAMPLE_OUTLINE))

        assert isinstance(result, str)
        assert len(result) > 0

    def test_write_empty_llm_response_returns_empty(self):
        from app.blog.pipeline.generate import DraftWriter
        from app.blog.schemas.outline import OutlineJSON

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response("")

        with patch("app.blog.pipeline.generate.get_llm_client", return_value=mock_client):
            writer = DraftWriter()
            result = writer.write(SAMPLE_PRODUCT_JSON, OutlineJSON(**SAMPLE_OUTLINE))

        assert result == ""

    def test_write_draft_contains_h2(self):
        from app.blog.pipeline.generate import DraftWriter
        from app.blog.schemas.outline import OutlineJSON

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response(SAMPLE_DRAFT)

        with patch("app.blog.pipeline.generate.get_llm_client", return_value=mock_client):
            writer = DraftWriter()
            result = writer.write(SAMPLE_PRODUCT_JSON, OutlineJSON(**SAMPLE_OUTLINE))

        assert "##" in result


class TestReviewAgent:
    def test_review_returns_review_result(self):
        from app.blog.pipeline.review import ReviewAgent
        from app.blog.schemas.review import ReviewResult
        from app.blog.schemas.outline import OutlineJSON

        review_data = {"pass": True, "issues": [], "revised_draft": SAMPLE_DRAFT}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response(
            json.dumps(review_data)
        )

        with patch("app.blog.pipeline.review.get_llm_client", return_value=mock_client):
            agent = ReviewAgent()
            result = agent.review(SAMPLE_PRODUCT_JSON, OutlineJSON(**SAMPLE_OUTLINE), SAMPLE_DRAFT)

        assert isinstance(result, ReviewResult)
        assert result.passed is True
        assert result.revised_draft == SAMPLE_DRAFT

    def test_review_parses_issues(self):
        from app.blog.pipeline.review import ReviewAgent
        from app.blog.schemas.outline import OutlineJSON

        review_data = {
            "pass": False,
            "issues": [
                {"type": "forbidden_expression", "text": "혁신적인 서비스", "reason": "금지 표현"}
            ],
            "revised_draft": SAMPLE_DRAFT,
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response(
            json.dumps(review_data)
        )

        with patch("app.blog.pipeline.review.get_llm_client", return_value=mock_client):
            agent = ReviewAgent()
            result = agent.review(SAMPLE_PRODUCT_JSON, OutlineJSON(**SAMPLE_OUTLINE), SAMPLE_DRAFT)

        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0].type == "forbidden_expression"

    def test_review_fallback_preserves_draft(self):
        from app.blog.pipeline.review import ReviewAgent
        from app.blog.schemas.outline import OutlineJSON

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _llm_response("invalid json")

        with patch("app.blog.pipeline.review.get_llm_client", return_value=mock_client):
            agent = ReviewAgent()
            result = agent.review(SAMPLE_PRODUCT_JSON, OutlineJSON(**SAMPLE_OUTLINE), SAMPLE_DRAFT)

        assert result.revised_draft == SAMPLE_DRAFT


# ─── Orchestrator / Pipeline tests ────────────────────────────────────────────

class TestBlogPipeline:
    def _make_mock_clients(self, outline_json, draft_text, review_json):
        """Mock LLM calls for all 3 agents (3 separate client instances)."""
        def _client_factory():
            c = MagicMock()
            return c

        outline_client = MagicMock()
        outline_client.chat.completions.create.return_value = _llm_response(outline_json)

        draft_client = MagicMock()
        draft_client.chat.completions.create.return_value = _llm_response(draft_text)

        review_client = MagicMock()
        review_client.chat.completions.create.return_value = _llm_response(review_json)

        return outline_client, draft_client, review_client

    def test_pipeline_returns_generate_post_response(self):
        from app.blog.pipeline.orchestrator import BlogPipeline
        from app.blog.schemas.response import GeneratePostResponse
        from app.blog.schemas.review import PipelineStatus

        review_data = {"pass": True, "issues": [], "revised_draft": SAMPLE_DRAFT}
        outline_c, draft_c, review_c = self._make_mock_clients(
            json.dumps(SAMPLE_OUTLINE), SAMPLE_DRAFT, json.dumps(review_data)
        )

        call_count = [0]

        def rotating_client():
            i = call_count[0]
            call_count[0] += 1
            return [outline_c, draft_c, review_c][i]

        with patch("app.blog.pipeline.generate.get_llm_client", side_effect=rotating_client), \
             patch("app.blog.pipeline.review.get_llm_client", return_value=review_c):
            pipeline = BlogPipeline()
            result = pipeline.run(SAMPLE_PRODUCT_JSON)

        assert isinstance(result, GeneratePostResponse)
        assert result.status == PipelineStatus.FINALIZED

    def test_pipeline_status_is_finalized(self):
        from app.blog.pipeline.orchestrator import BlogPipeline
        from app.blog.schemas.review import PipelineStatus

        review_data = {"pass": False, "issues": [], "revised_draft": SAMPLE_DRAFT}

        with patch("app.blog.pipeline.generate.OutlineGenerator.generate") as mock_outline, \
             patch("app.blog.pipeline.generate.DraftWriter.write") as mock_draft, \
             patch("app.blog.pipeline.review.ReviewAgent.review") as mock_review:

            from app.blog.schemas.outline import OutlineJSON
            from app.blog.schemas.review import ReviewResult
            mock_outline.return_value = OutlineJSON(**SAMPLE_OUTLINE)
            mock_draft.return_value = SAMPLE_DRAFT
            mock_review.return_value = ReviewResult(
                passed=False, issues=[], revised_draft=SAMPLE_DRAFT
            )

            pipeline = BlogPipeline()
            result = pipeline.run(SAMPLE_PRODUCT_JSON)

        assert result.status == PipelineStatus.FINALIZED
        assert result.final_draft == SAMPLE_DRAFT

    def test_pipeline_final_draft_falls_back_when_revision_empty(self):
        from app.blog.pipeline.orchestrator import BlogPipeline

        with patch("app.blog.pipeline.generate.OutlineGenerator.generate") as mock_outline, \
             patch("app.blog.pipeline.generate.DraftWriter.write") as mock_draft, \
             patch("app.blog.pipeline.review.ReviewAgent.review") as mock_review:

            from app.blog.schemas.outline import OutlineJSON
            from app.blog.schemas.review import ReviewResult
            mock_outline.return_value = OutlineJSON(**SAMPLE_OUTLINE)
            mock_draft.return_value = SAMPLE_DRAFT
            mock_review.return_value = ReviewResult(
                passed=False, issues=[], revised_draft=""
            )

            pipeline = BlogPipeline()
            result = pipeline.run(SAMPLE_PRODUCT_JSON)

        assert result.final_draft == SAMPLE_DRAFT

    def test_pipeline_evidence_map_in_response(self):
        from app.blog.pipeline.orchestrator import BlogPipeline

        with patch("app.blog.pipeline.generate.OutlineGenerator.generate") as mock_outline, \
             patch("app.blog.pipeline.generate.DraftWriter.write") as mock_draft, \
             patch("app.blog.pipeline.review.ReviewAgent.review") as mock_review:

            from app.blog.schemas.outline import OutlineJSON
            from app.blog.schemas.review import ReviewResult
            mock_outline.return_value = OutlineJSON(**SAMPLE_OUTLINE)
            mock_draft.return_value = SAMPLE_DRAFT
            mock_review.return_value = ReviewResult(
                passed=True, issues=[], revised_draft=SAMPLE_DRAFT
            )

            pipeline = BlogPipeline()
            result = pipeline.run(SAMPLE_PRODUCT_JSON)

        assert isinstance(result.evidence_map, dict)
        assert len(result.evidence_map) > 0

    def test_pipeline_all_three_categories(self):
        """Pipeline must work for all 3 categories."""
        from app.blog.pipeline.orchestrator import BlogPipeline

        for article_json in [SAMPLE_PRODUCT_JSON, SAMPLE_FOODTECH_JSON, SAMPLE_TREND_JSON]:
            with patch("app.blog.pipeline.generate.OutlineGenerator.generate") as mock_outline, \
                 patch("app.blog.pipeline.generate.DraftWriter.write") as mock_draft, \
                 patch("app.blog.pipeline.review.ReviewAgent.review") as mock_review:

                from app.blog.schemas.outline import OutlineJSON, OutlineSection
                from app.blog.schemas.review import ReviewResult
                from app.blog.templates import get_template

                tmpl = get_template(article_json["category"])
                sections = [
                    OutlineSection(heading=h, points=["p"])
                    for h in tmpl.sections
                ]
                mock_outline.return_value = OutlineJSON(
                    title="T", lead_angle="L", sections=sections,
                    evidence_map=tmpl.evidence_map
                )
                mock_draft.return_value = SAMPLE_DRAFT
                mock_review.return_value = ReviewResult(
                    passed=True, issues=[], revised_draft=SAMPLE_DRAFT
                )

                pipeline = BlogPipeline()
                result = pipeline.run(article_json)

            assert result.status.value == "FINALIZED"


# ─── API endpoint tests ───────────────────────────────────────────────────────

class TestGenerateOutlineEndpoint:
    def test_returns_200_with_valid_input(self, client):
        from app.blog.schemas.outline import OutlineJSON

        with patch("app.blog.pipeline.generate.OutlineGenerator.generate") as mock_gen:
            mock_gen.return_value = OutlineJSON(**SAMPLE_OUTLINE)
            resp = client.post(
                "/generate-outline",
                json={"article_json": SAMPLE_PRODUCT_JSON},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OUTLINE_CREATED"
        assert "outline" in data
        assert "title" in data["outline"]
        assert "sections" in data["outline"]

    def test_returns_422_on_empty_json(self, client):
        resp = client.post("/generate-outline", json={"article_json": {}})
        assert resp.status_code == 422

    def test_returns_422_on_invalid_category(self, client):
        resp = client.post(
            "/generate-outline",
            json={"article_json": {"category": "잘못된카테고리"}},
        )
        assert resp.status_code == 422

    def test_returns_422_on_missing_article_json(self, client):
        resp = client.post("/generate-outline", json={})
        assert resp.status_code == 422


class TestGenerateDraftEndpoint:
    def test_returns_200_with_valid_input(self, client):
        with patch("app.blog.pipeline.generate.DraftWriter.write") as mock_write:
            mock_write.return_value = SAMPLE_DRAFT
            resp = client.post(
                "/generate-draft",
                json={
                    "article_json": SAMPLE_PRODUCT_JSON,
                    "outline": SAMPLE_OUTLINE,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DRAFT_CREATED"
        assert "draft" in data
        assert data["draft"] == SAMPLE_DRAFT

    def test_returns_422_on_missing_outline(self, client):
        resp = client.post(
            "/generate-draft",
            json={"article_json": SAMPLE_PRODUCT_JSON},
        )
        assert resp.status_code == 422

    def test_returns_422_on_invalid_outline_section_count(self, client):
        bad_outline = {
            "title": "T",
            "lead_angle": "L",
            "sections": [{"heading": "only one", "points": []}],
        }
        resp = client.post(
            "/generate-draft",
            json={"article_json": SAMPLE_PRODUCT_JSON, "outline": bad_outline},
        )
        assert resp.status_code == 422


class TestReviewDraftEndpoint:
    def test_returns_200_review_passed(self, client):
        from app.blog.schemas.review import ReviewResult

        with patch("app.blog.pipeline.review.ReviewAgent.review") as mock_review:
            mock_review.return_value = ReviewResult(
                passed=True, issues=[], revised_draft=SAMPLE_DRAFT
            )
            resp = client.post(
                "/review-draft",
                json={
                    "article_json": SAMPLE_PRODUCT_JSON,
                    "outline": SAMPLE_OUTLINE,
                    "draft": SAMPLE_DRAFT,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REVIEW_PASSED"
        assert data["review_passed"] is True
        assert data["issues"] == []
        assert "revised_draft" in data

    def test_returns_200_review_failed(self, client):
        from app.blog.schemas.review import ReviewResult, ReviewIssue

        with patch("app.blog.pipeline.review.ReviewAgent.review") as mock_review:
            mock_review.return_value = ReviewResult(
                passed=False,
                issues=[ReviewIssue(type="forbidden_expression", text="혁신", reason="금지")],
                revised_draft=SAMPLE_DRAFT,
            )
            resp = client.post(
                "/review-draft",
                json={
                    "article_json": SAMPLE_PRODUCT_JSON,
                    "outline": SAMPLE_OUTLINE,
                    "draft": SAMPLE_DRAFT,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REVIEW_FAILED"
        assert data["review_passed"] is False
        assert len(data["issues"]) == 1

    def test_returns_422_on_missing_draft(self, client):
        resp = client.post(
            "/review-draft",
            json={"article_json": SAMPLE_PRODUCT_JSON, "outline": SAMPLE_OUTLINE},
        )
        assert resp.status_code == 422


class TestGeneratePostEndpoint:
    def test_returns_200_with_all_fields(self, client):
        from app.blog.schemas.review import ReviewResult, PipelineStatus
        from app.blog.schemas.outline import OutlineJSON
        from app.blog.schemas.response import GeneratePostResponse

        expected_response = GeneratePostResponse(
            status=PipelineStatus.FINALIZED,
            outline=OutlineJSON(**SAMPLE_OUTLINE),
            draft=SAMPLE_DRAFT,
            review_passed=True,
            issues=[],
            final_draft=SAMPLE_DRAFT,
            evidence_map=SAMPLE_OUTLINE["evidence_map"],
        )

        with patch("app.blog.pipeline.orchestrator.BlogPipeline.run") as mock_run:
            mock_run.return_value = expected_response
            resp = client.post(
                "/generate-post",
                json={"article_json": SAMPLE_PRODUCT_JSON},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "FINALIZED"
        assert "outline" in data
        assert "draft" in data
        assert "review_passed" in data
        assert "issues" in data
        assert "final_draft" in data
        assert "evidence_map" in data

    def test_returns_422_on_empty_json(self, client):
        resp = client.post("/generate-post", json={"article_json": {}})
        assert resp.status_code == 422

    def test_returns_422_on_invalid_category(self, client):
        resp = client.post(
            "/generate-post",
            json={"article_json": {"category": "invalid"}},
        )
        assert resp.status_code == 422

    def test_response_status_finalized(self, client):
        from app.blog.schemas.review import ReviewResult, PipelineStatus
        from app.blog.schemas.outline import OutlineJSON
        from app.blog.schemas.response import GeneratePostResponse

        resp_obj = GeneratePostResponse(
            status=PipelineStatus.FINALIZED,
            outline=OutlineJSON(**SAMPLE_OUTLINE),
            draft=SAMPLE_DRAFT,
            review_passed=False,
            issues=[],
            final_draft=SAMPLE_DRAFT,
            evidence_map={},
        )

        with patch("app.blog.pipeline.orchestrator.BlogPipeline.run", return_value=resp_obj):
            resp = client.post(
                "/generate-post",
                json={"article_json": SAMPLE_PRODUCT_JSON},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "FINALIZED"


# ─── LLM utility tests ────────────────────────────────────────────────────────

class TestParseJsonResponse:
    def test_valid_json(self):
        from app.blog.pipeline.llm import parse_json_response
        result = parse_json_response('{"key": "value"}', {})
        assert result == {"key": "value"}

    def test_json_in_code_fence(self):
        from app.blog.pipeline.llm import parse_json_response
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_response(text, {})
        assert result == {"key": "value"}

    def test_invalid_json_returns_fallback(self):
        from app.blog.pipeline.llm import parse_json_response
        fallback = {"default": True}
        result = parse_json_response("not json at all", fallback)
        assert result == fallback

    def test_partial_json_extraction(self):
        from app.blog.pipeline.llm import parse_json_response
        text = 'some prefix {"key": 42} some suffix'
        result = parse_json_response(text, {})
        assert result == {"key": 42}
