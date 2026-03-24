0. 전체 개요
목적
정규화된 기사 JSON을 입력받아구조화된 산업형 블로그 포스팅을 자동 생성하는 파이프라인을 구현한다.

전체 플로우
[Normalized JSON]
   ↓
[Outline Generator]
   ↓
[Outline JSON]
   ↓
[Draft Writer]
   ↓
[Draft v1]
   ↓
[Review Agent]
   ↓
[Final Draft]

핵심 제약 (전역 규칙)
1. JSON에 없는 사실 생성 금지
2. 과장/광고 표현 금지
3. 시사점은 "가능성 수준"만 허용
4. 모든 문장은 JSON 기반이어야 함

1. 입력 JSON 스키마 (고정)
{
  "version": "1.0.0",
  "categories": {
    "해외 동향": {
      "completion_thresholds": {
        "completed": 0.85,
        "partial_completed": 0.6
      },
      "fields": [
        {
          "field_path": "category",
          "required": true,
          "type": "string",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "topic",
          "required": true,
          "type": "string",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "researched_at",
          "required": true,
          "type": "datetime",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "sources_master",
          "required": true,
          "type": "array",
          "min_items": 1,
          "must_have_sources": false,
          "weight": 1.5
        },
        {
          "field_path": "trend_name",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "definition",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "change_from_previous",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "background",
          "required": true,
          "type": "array_of_value_with_sources",
          "min_items": 1,
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "core_change_structure.product_change",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "core_change_structure.consumption_change",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "cases",
          "required": true,
          "type": "array",
          "min_items": 2,
          "must_have_sources": true,
          "weight": 2.0
        },
        {
          "field_path": "cases[].company",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.0
        },
        {
          "field_path": "cases[].product_or_service",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.0
        },
        {
          "field_path": "cases[].how_it_works",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.0
        },
        {
          "field_path": "cases[].features",
          "required": true,
          "type": "array_of_value_with_sources",
          "min_items": 1,
          "must_have_sources": true,
          "weight": 1.0
        },
        {
          "field_path": "expansion_pattern.geographic_scope",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "expansion_pattern.industry_expansion",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        }
      ]
    },
    "상품·서비스": {
      "completion_thresholds": {
        "completed": 0.85,
        "partial_completed": 0.6
      },
      "fields": [
        {
          "field_path": "category",
          "required": true,
          "type": "string",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "topic",
          "required": true,
          "type": "string",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "researched_at",
          "required": true,
          "type": "datetime",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "sources_master",
          "required": true,
          "type": "array",
          "min_items": 1,
          "must_have_sources": false,
          "weight": 1.5
        },
        {
          "field_path": "name",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "summary",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "developer.company_name",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "developer.company_description",
          "required": false,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 0.75
        },
        {
          "field_path": "purpose",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "key_features",
          "required": true,
          "type": "array_of_value_with_sources",
          "min_items": 2,
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "how_it_works",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "data_or_technology_basis",
          "required": true,
          "type": "array_of_value_with_sources",
          "min_items": 1,
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "business_model.pricing",
          "required": false,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.0,
          "allow_literal_values": [
            "비공개"
          ]
        },
        {
          "field_path": "business_model.model",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "use_effects",
          "required": true,
          "type": "array_of_value_with_sources",
          "min_items": 1,
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "differentiation",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        }
      ]
    },
    "푸드테크": {
      "completion_thresholds": {
        "completed": 0.85,
        "partial_completed": 0.6
      },
      "fields": [
        {
          "field_path": "category",
          "required": true,
          "type": "string",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "topic",
          "required": true,
          "type": "string",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "researched_at",
          "required": true,
          "type": "datetime",
          "must_have_sources": false,
          "weight": 1.0
        },
        {
          "field_path": "sources_master",
          "required": true,
          "type": "array",
          "min_items": 1,
          "must_have_sources": false,
          "weight": 1.5
        },
        {
          "field_path": "technology_name",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "summary",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "technology_principle",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "problem_with_existing_method",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "solution",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "applications",
          "required": true,
          "type": "array",
          "min_items": 1,
          "must_have_sources": true,
          "weight": 1.5
        },
        {
          "field_path": "applications[].company",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.0
        },
        {
          "field_path": "applications[].application_form",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.0
        },
        {
          "field_path": "results_and_effects",
          "required": true,
          "type": "array_of_value_with_sources",
          "min_items": 1,
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "use_cases",
          "required": true,
          "type": "array_of_value_with_sources",
          "min_items": 1,
          "must_have_sources": true,
          "weight": 1.25
        },
        {
          "field_path": "industry_meaning",
          "required": true,
          "type": "value_with_sources",
          "must_have_sources": true,
          "weight": 1.5
        }
      ]
    }
  },
  "global_rules": {
    "value_field_empty_values": [
      "",
      null
    ],
    "default_max_iterations": 3,
    "default_min_completion_rate": 0.95,
    "min_sources_required": 3,
    "partial_completion_rate_floor": 0.6,
    "notes_do_not_affect_completion_rate": true,
    "all_non_empty_values_must_reference_sources_master": true,
    "source_id_pattern": "^S[1-9][0-9]*$"
  }
}


2. Agent 1 — Outline Generator
역할
JSON을 기반으로 글 구조만 생성 (문장 X, 구조만 O)

입력
{
  "article_json": {...},
  "category_template": {...}
}

출력 스키마 (고정)
{
  "title": "",
  "lead_angle": "",
  "sections": [
    {
      "heading": "",
      "points": []
    }
  ]
}

생성 규칙 (강제)
1. JSON에 없는 내용 절대 추가 금지
2. 섹션 수: 4~6개 고정
3. heading은 명사형 or 설명형
4. points는 문장 X → bullet 수준
5. 시사점은 마지막 섹션에만 위치
6. 시사점은 반드시 implications_seed 기반

카테고리별 템플릿 (필수 적용)
상품/서비스
[
  "서비스 개요",
  "개발 배경 / 해결 문제",
  "핵심 기능",
  "이용 방식 / 도입 방식",
  "시사점"
]

푸드테크
[
  "기술 개요",
  "기존 한계와 해결 방식",
  "적용 방식",
  "상용화 단계",
  "시사점"
]

해외 동향
[
  "트렌드 개요",
  "발생 배경",
  "구조적 변화",
  "주요 사례",
  "확산 가능성 / 시사점"
]

출력 예시 (강화 버전)
{
  "title": "10년치 해외 식품 데이터 기반 AI ‘FOODIAL AI’ 출시",
  "lead_angle": "일본 TNC가 축적된 식품 트렌드 데이터를 기반으로 대화형 AI 서비스를 선보였다.",
  "sections": [
    {
      "heading": "서비스 개요",
      "points": [
        "TNC가 2026년 FOODIAL AI 출시",
        "10년치 FOODIAL 리포트 기반",
        "해외 식품 트렌드 분석 특화 AI"
      ]
    },
    {
      "heading": "개발 배경 / 해결 문제",
      "points": [
        "해외 식품 정보 탐색 어려움",
        "리포트 분석 시간 부담",
        "시장 적용 판단의 어려움"
      ]
    },
    {
      "heading": "핵심 기능",
      "points": [
        "리포트 기반 통합 검색 및 요약",
        "근거 기반 아이디어 도출",
        "정보 없음 응답 설계"
      ]
    },
    {
      "heading": "이용 방식 / 도입 방식",
      "points": [
        "B2B 리포트 구독 기반",
        "기업 대상 서비스 제공"
      ]
    },
    {
      "heading": "시사점",
      "points": [
        "산업 특화 데이터 기반 AI 사례",
        "상품기획 효율화 가능성"
      ]
    }
  ]
}

3. Agent 2 — Draft Writer
역할
Outline + JSON → 실제 블로그 글 생성

입력
{
  "article_json": {...},
  "outline_json": {...}
}

출력
완성된 블로그 글 (string)

문체 규칙 (강제)
- 산업 리포트 스타일
- 과장 없음
- 짧은 문단
- 정보 중심
- 해석 최소화

구조 규칙 (강제)
1. 제목 → H2
2. 리드 → 1~2문단
3. 섹션 → H3 + 내용
4. bullet 사용 허용 (ㅇ, ·, ①②③)

생성 규칙 (중요)
1. 기능 vs 해석 분리
기능 = JSON 기반
시사점 = implications_seed 기반 확장

2. 금지 표현
혁신적
획기적
압도적
게임체인저
시장 재편
완전히 바꾼다

3. 허용 표현
~로 볼 수 있다
~ 가능성이 있다
~에 기여할 수 있다

출력 예시 (확장형)
## 10년치 해외 식품 데이터 기반 AI ‘FOODIAL AI’ 출시

일본의 식품 리서치 기업 TNC가 축적된 해외 식품 트렌드 데이터를 기반으로 한 대화형 AI 서비스 ‘FOODIAL AI’를 선보였다. 이 서비스는 2015년 이후 축적된 리포트와 자체 리서치를 활용해 식품·음료 업계의 시장조사와 상품기획 과정을 지원하는 것이 특징이다.

### 1. 서비스 개요
ㅇ TNC는 2026년 FOODIAL AI를 정식 출시했다.  
ㅇ 해당 서비스는 10년 이상 축적된 FOODIAL 리포트를 주요 데이터로 활용한다.

### 2. 개발 배경 / 해결 문제
ㅇ 식품 업계에서는 신뢰할 수 있는 해외 시장 정보를 확보하기 어렵다.  
ㅇ 또한 방대한 리포트를 분석하는 데 많은 시간이 소요되는 문제가 존재한다.

### 3. 핵심 기능
① 통합 검색 및 요약  
· 과거 리포트를 기반으로 트렌드와 시장 정보를 검색·요약한다.

② 근거 기반 아이디어 도출  
· 단순 정보 제공이 아니라 상품 콘셉트 도출까지 지원한다.

③ 신뢰성 중심 설계  
· 데이터가 없을 경우 ‘정보 없음’으로 응답한다.

### 4. 이용 방식
ㅇ 해당 서비스는 B2B 유료 리포트 구독 기반으로 제공된다.

### 5. 시사점
ㅇ 산업 특화 데이터 기반 AI 서비스 사례로 볼 수 있다.  
ㅇ 향후 상품기획 및 시장조사 과정의 효율화에 기여할 가능성이 있다.

4. Agent 3 — Review Agent
역할
초안 품질 검증 + 수정

입력
{
  "article_json": {...},
  "outline_json": {...},
  "draft": "..."
}

출력 (실무 추천)
{
  "pass": false,
  "issues": [
    {
      "type": "unsupported_claim",
      "text": "",
      "reason": ""
    }
  ],
  "revised_draft": ""
}

검수 기준
1. 사실성
모든 문장이 JSON 기반인가?
없는 정보 추가됐는가?

2. 구조
섹션 누락/순서 오류 있는가?

3. 과장
금지 표현 포함 여부

4. 시사점 안전성
단정 표현 여부

5. 가독성
문단 길이 / 반복 여부

수정 예시
{
  "type": "tone_violation",
  "before": "시장을 재편할 것으로 보인다",
  "after": "시장에 영향을 줄 가능성이 있다"
}

5. 상태 관리 (필수)
EXTRACTED
NORMALIZED
OUTLINE_CREATED
DRAFT_CREATED
REVIEW_FAILED
REVIEW_PASSED
FINALIZED

6. 내부 구조 (코드 설계)
/prompts
  outline.ts
  draft.ts
  review.ts

/templates
  product.ts
  foodtech.ts
  trend.ts

/pipeline
  generate.ts
  review.ts

7. 핵심 구현 포인트 (중요)
1. 절대 금지
글쓰기 단계에서 검색 금지

2. 시사점 통제
implications_seed 기반만 확장

3. evidence mapping (권장)
{
  "p1": ["entity_name", "summary"],
  "p2": ["background"],
  "p3": ["core_features"]
}

🔥 최종 요약 (개발자용 한 줄)
"JSON 기반 → 구조 생성 → 문장 생성 → 검수 수정" 3단계 파이프라인을 구현한다.

