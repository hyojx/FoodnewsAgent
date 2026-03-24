# 1. 제품 한 줄 정의

**원문 기사 URL과 카테고리를 입력받아, 카테고리별 목표 JSON 스키마를 기준으로 부족한 정보를 반복 검색·수집·검증하여 구조화된 조사 결과 JSON을 반환하는 API 기반 리서치 에이전트**

이 정의는 기존 PRD와 동일한 방향이고, 구현 포인트는 다음 4개다.

* 입력: `article_url`, `category`
* 처리: 기사 파싱 → 1차 추출 → 누락 필드 탐지 → 재검색/보강 반복
* 출력: 카테고리별 최종 조사 JSON + 메타데이터
* 저장: 요청, 출처, 필드 상태, 반복 로그, 결과 저장  

---

# 2. MVP 범위

## v0

* `POST /v1/research`
* `GET /v1/research/{request_id}`
* 원문 기사 파싱
* 카테고리별 스키마 로딩
* 1차 LLM 추출
* 결과 JSON 저장

## v1

* 유사 기사 검색 3~5건
* `sources_master` 누적
* source 기반 값만 허용

## v2

* 누락 필드 탐지
* 필드별 재검색어 생성
* 최대 3회 반복 보강

## v3

* completion_rate 계산
* partial_completed / failed 구분
* 필드별 confidence_score 저장

## v4

* 중복 제거 고도화
* source 충돌 해결 규칙 적용
* 운영용 에러코드/로그 정교화

---

# 3. 최종 입력 / 출력 계약

## 3.1 요청

### `POST /v1/research`

```json
{
  "article_url": "https://example.com/article",
  "category": "해외 동향",
  "options": {
    "max_iterations": 3,
    "min_completion_rate": 0.85,
    "locale": "ko-KR",
    "search_limit_per_iteration": 5
  }
}
```

## 3.2 응답

즉시 처리형이 아니라면 PRD대로 `request_id`를 먼저 반환하는 구조가 맞다. 

```json
{
  "request_id": "req_20260324_001",
  "status": "queued"
}
```

## 3.3 조회

### `GET /v1/research/{request_id}`

```json
{
  "request_id": "req_20260324_001",
  "status": "partial_completed",
  "category": "해외 동향",
  "article_url": "https://example.com/article",
  "completion_rate": 0.82,
  "iterations_count": 3,
  "missing_fields": [
    "cases[1].how_it_works",
    "expansion_pattern.industry_expansion"
  ],
  "result": {
    "...": "카테고리별 최종 JSON"
  },
  "meta": {
    "created_at": "2026-03-24T09:00:00+09:00",
    "started_at": "2026-03-24T09:00:05+09:00",
    "finished_at": "2026-03-24T09:01:42+09:00",
    "sources_used": 7
  }
}
```

---

# 4. 카테고리별 최종 JSON 스키마 운영 원칙

네가 준 JSON을 **출력 스키마**로 확정하고, 여기에 공통 규칙만 추가해서 운영하는 방식이 가장 깔끔하다.

## 4.1 공통 필드 규칙

모든 카테고리에 공통으로 적용:

* `category`: 요청값 그대로
* `topic`: 원문 기사와 조사 내용을 바탕으로 생성한 조사 주제명
* `researched_at`: ISO 8601 datetime
* `sources_master`: 실제 사용한 출처 마스터 목록
* 각 세부 필드의 `sources`: 반드시 `sources_master.source_id`만 참조
* source 없는 값은 최종 저장 금지 

## 4.2 source_id 규칙

```text
S1, S2, S3 ...
```

* 요청 단위로 재할당
* URL 중복이면 같은 source_id 사용
* 동일 기사 재전재라도 URL/본문이 다르면 별도 저장 후 `is_duplicate=true` 처리 가능

---

# 5. 카테고리별 필수/선택/최소 개수 규칙

이 부분이 completion_rate 계산의 핵심이다.

## 5.1 해외 동향

### 필수 필드

* `category`
* `topic`
* `researched_at`
* `sources_master`
* `trend_name.value`
* `definition.value`
* `change_from_previous.value`
* `background`
* `core_change_structure.product_change.value`
* `core_change_structure.consumption_change.value`
* `cases`
* `expansion_pattern.geographic_scope.value`
* `expansion_pattern.industry_expansion.value`

### 최소 개수

* `sources_master`: 2개 이상 권장, MVP는 1개 이상
* `background`: 1개 이상
* `cases`: 2개 이상
* `cases[].features`: 각 사례당 1개 이상

### 완료 판정

* `trend_name`, `definition`, `change_from_previous`는 `value`와 `sources`가 모두 있어야 완료
* `background[0].value`만 있고 source가 없으면 미완성
* `cases`가 1개뿐이면 부분 채움으로 간주
* `expansion_pattern`은 geographic/industry 둘 다 있어야 완료

## 5.2 상품·서비스

### 필수 필드

* `category`
* `topic`
* `researched_at`
* `sources_master`
* `name.value`
* `summary.value`
* `developer.company_name.value`
* `purpose.value`
* `key_features`
* `how_it_works.value`
* `data_or_technology_basis`
* `business_model.model.value`
* `use_effects`
* `differentiation.value`

### 조건부 필수

* `business_model.pricing.value`: 가격 정보가 공개된 경우 필수, 비공개면 `"비공개"` + notes
* `developer.company_description.value`: 찾을 수 있으면 채움, 없으면 partial 허용

### 최소 개수

* `key_features`: 2개 이상
* `data_or_technology_basis`: 1개 이상
* `use_effects`: 1개 이상

## 5.3 푸드테크

### 필수 필드

* `category`
* `topic`
* `researched_at`
* `sources_master`
* `technology_name.value`
* `summary.value`
* `technology_principle.value`
* `problem_with_existing_method.value`
* `solution.value`
* `applications`
* `results_and_effects`
* `use_cases`
* `industry_meaning.value`

### 최소 개수

* `applications`: 1개 이상
* `results_and_effects`: 1개 이상
* `use_cases`: 1개 이상

### 완료 판정

* 기술 원리 설명이 너무 추상적이면 `confidence_score` 낮춤
* `applications[].company.value` 없이 application_form만 있으면 부분 채움 처리

---

# 6. completion_rate 계산 규칙

PRD의 공백 탐지/종료 조건을 실제 구현용으로 수치화하면 아래가 가장 실무적이다. 

## 6.1 필드 단위 점수

각 필드를 아래처럼 평가:

* 1.0 = 값 있음 + source 있음 + 최소 개수 충족 + confidence 기준 충족
* 0.5 = 값은 있으나 source 부족 / 최소 개수 미달 / 표현이 너무 추상적
* 0.0 = 비어 있음 또는 무효

## 6.2 배열 필드 점수

예: `cases` 최소 2개 필요일 때

* 0개: 0
* 1개: 0.5
* 2개 이상: 1

예: `key_features` 최소 2개 필요일 때

* 0개: 0
* 1개: 0.5
* 2개 이상: 1

## 6.3 completion_rate 공식

```text
completion_rate = (각 평가 대상 필드 점수 합) / (총 평가 대상 필드 수)
```

## 6.4 권장 기준

* `>= 0.90`: completed
* `0.65 ~ 0.89`: partial_completed
* `< 0.65`: failed 또는 low_quality_partial

MVP에서는 아래처럼 단순화해도 충분하다.

* `completed`: `completion_rate >= 0.85`
* `partial_completed`: `0.60 <= completion_rate < 0.85`
* `failed`: `completion_rate < 0.60` 또는 치명적 오류

---

# 7. 필드별 완료 기준표

## 7.1 공통 규칙

다음 중 하나면 미완성으로 본다. 이는 기존 PRD의 공백 탐지 기준을 코드화한 것이다. 

* `value == ""`
* `value == null`
* `sources.length == 0`
* 배열 필드 길이 0
* 최소 요구 개수 미달
* confidence score 임계치 미만

## 7.2 notes 필드 규칙

`notes`는 completion_rate 대상이 아님.
다만 다음 용도로 적극 사용:

* 공개 가격 미확인
* source 간 충돌
* 기사에는 없고 기업 공식 사이트에서만 확인됨
* 용어 해석상 주의 필요

## 7.3 “추측 금지” 규칙

PRD의 품질 관리 요구사항대로, source 없는 추정값은 금지한다. 

허용:

* `"pricing.value": "비공개"` + source 존재 + `notes` 설명

금지:

* 근거 없이 `"pricing.value": "월 9.99달러 추정"`

---

# 8. 검색 전략 규칙

이건 바이브 코딩할 때 가장 필요한 부분이다.

## 8.1 전체 검색 흐름

PRD의 전체 플로우를 구현형으로 풀면 아래다. 

### 1단계: 원문 기사 파싱

* title
* publisher
* published_at
* cleaned_content
* article language

### 2단계: 1차 추출

원문 기사만으로 target schema를 1차 채움

### 3단계: 누락 필드 탐지

* 빈 필드
* source 없는 필드
* 최소 개수 미달 필드 탐지

### 4단계: 필드별 검색어 생성

누락 필드 기준으로 검색어 생성

### 5단계: 외부 검색

* 유사 기사
* 기업 공식 사이트
* 제품 페이지
* 보도자료
* 기술 설명 자료

### 6단계: source 정제

* 중복 제거
* 저품질 source 제거
* 충돌 정보 표시

### 7단계: 재추출 / 병합

새 source를 반영해 스키마 보강

### 8단계: 종료 조건 검사

* completion_rate 달성
* max_iterations 초과
* 더 이상 유효 정보 없음
* 동일 필드 연속 미보강 

## 8.2 검색 우선순위

1. 원문 기사
2. 동일 주제의 신뢰 가능한 언론 기사
3. 기업 공식 사이트 / 제품 페이지
4. 공식 보도자료
5. 투자자 자료 / 기술 소개 자료
6. 업계 분석 글

## 8.3 source_type enum

```text
article
official_site
press_release
product_page
report
blog
video
other
```

## 8.4 필드별 추천 검색어 패턴

### 해외 동향

* `"[기사 제목]" similar article`
* `"[trend_name]" definition`
* `"[trend_name]" market trend`
* `"[trend_name]" examples brands`
* `"[trend_name]" expansion global industry`

### 상품·서비스

* `"[product name]" official site`
* `"[product name]" pricing`
* `"[product name]" features`
* `"[developer name]" company`
* `"[product name]" how it works`

### 푸드테크

* `"[technology name]" principle`
* `"[technology name]" applications food`
* `"[technology name]" company case`
* `"[technology name]" results efficiency`
* `"[technology name]" industry implications`

## 8.5 필드-검색어 매핑 예시

```json
{
  "cases": [
    "trend example brands",
    "company using trend",
    "product/service case study"
  ],
  "business_model.pricing": [
    "product pricing",
    "official pricing page",
    "subscription plan"
  ],
  "technology_principle": [
    "technology principle",
    "how technology works",
    "mechanism"
  ]
}
```

---

# 9. source 신뢰도 정책

결과 품질을 흔드는 핵심이라 꼭 고정해두는 게 좋다.

## 9.1 신뢰도 우선순위

높음 → 낮음

1. 원문 기사 본문
2. 기업 공식 사이트
3. 공식 보도자료
4. 주요 언론
5. 업계 보고서
6. 일반 블로그 / 커뮤니티

## 9.2 필드별 최소 source 기준

### 단일 source 허용

* `summary`
* `definition`
* `technology_name`
* `name`
* `topic`

### 2개 이상 교차 확인 권장

* `pricing`
* `use_effects`
* `results_and_effects`
* `change_from_previous`
* `industry_meaning`
* `expansion_pattern`

## 9.3 source 충돌 처리

예:

* 기사 A: “미국 중심 확산”
* 기사 B: “유럽까지 확산”

처리:

* 더 최신 source 우선
* 공식 source 우선
* 둘 다 유효하면 넓은 표현으로 병합
* `notes`에 충돌 사실 기록

예시:

```json
{
  "value": "미국을 중심으로 확산됐으며 일부 유럽 시장에서도 확장 움직임이 확인된다.",
  "sources": ["S2", "S4"],
  "notes": "지역 확산 범위에 대해 source별 표현 차이가 있어 최신 기사와 공식 자료를 병합 정리함."
}
```

---

# 10. 실패 케이스 목록

PRD의 실패/부분완료 요구를 실제 예외 시나리오로 확장하면 아래가 필요하다. 

## 10.1 입력 단계

* URL 형식 오류
* 지원하지 않는 카테고리
* 차단된 도메인
* 중복 요청

## 10.2 기사 파싱 단계

* 본문 추출 실패
* 본문 너무 짧음
* 유료벽으로 본문 접근 불가
* 게시일 추출 실패
* 언어 판별 실패

## 10.3 검색 단계

* 검색 API 타임아웃
* 검색 결과 0건
* 결과가 모두 중복
* 결과가 저품질만 존재
* rate limit 초과

## 10.4 추출/병합 단계

* LLM이 스키마 형식 위반
* source_id 참조 누락
* hallucination 의심
* 필수 필드 지속 누락
* min case 수 불충족

## 10.5 종료 단계

* max_iterations 도달
* completion_rate 미달
* 동일 필드 2회 연속 미보강 

---

# 11. 에러코드 표

```text
REQ_001  INVALID_URL
REQ_002  INVALID_CATEGORY
REQ_003  DUPLICATE_REQUEST

ART_001  ARTICLE_FETCH_FAILED
ART_002  ARTICLE_PARSE_FAILED
ART_003  ARTICLE_PAYWALLED
ART_004  ARTICLE_TOO_SHORT
ART_005  ARTICLE_PUBLISHED_AT_NOT_FOUND

SRCH_001 SEARCH_API_FAILED
SRCH_002 SEARCH_TIMEOUT
SRCH_003 SEARCH_NO_RESULTS
SRCH_004 SEARCH_RESULTS_ALL_DUPLICATED
SRCH_005 SEARCH_RATE_LIMITED

EXT_001  EXTRACTION_SCHEMA_INVALID
EXT_002  EXTRACTION_NO_EVIDENCE
EXT_003  EXTRACTION_LOW_CONFIDENCE
EXT_004  FIELD_MIN_ITEMS_NOT_MET

RES_001  COMPLETION_RATE_TOO_LOW
RES_002  MAX_ITERATIONS_REACHED
RES_003  NO_NEW_VALID_INFORMATION

SYS_001  INTERNAL_ERROR
SYS_002  DB_WRITE_FAILED
SYS_003  WORKER_TIMEOUT
```

## 에러 응답 예시

```json
{
  "request_id": "req_20260324_001",
  "status": "failed",
  "error": {
    "code": "ART_002",
    "message": "원문 기사 본문 추출에 실패했습니다."
  }
}
```

---

# 12. 상태값 정의

기존 PRD의 상태값을 그대로 사용하되 조금 더 명확하게 해석한다. 

```text
queued
processing
completed
partial_completed
failed
```

## 상태 정의

* `queued`: 요청 저장 완료, 아직 처리 전
* `processing`: 기사 파싱/검색/추출 진행 중
* `completed`: 목표 completion_rate 달성
* `partial_completed`: 일부 필드는 비었지만 반환 가능한 수준
* `failed`: 치명적 오류 또는 결과 품질 미달

---

# 13. 프롬프트 설계 초안

이건 바로 코드에 넣기 좋게 역할별로 나눈다.

## 13.1 Prompt A — 1차 추출

역할:

* 원문 기사 + 카테고리 + target schema를 받아 1차 채우기

핵심 규칙:

* 추측 금지
* 출처 없는 값 금지
* 모르면 빈 값 유지
* source_id는 `sources_master`에 있는 값만 사용

예시 프롬프트:

```text
You are a structured research extraction engine.

Your task is to fill the target JSON schema using only the provided source documents.
Do not infer unsupported facts.
Do not fabricate values.
Every non-empty field must reference one or more valid source_ids from sources_master.
If evidence is insufficient, leave the field empty.
Preserve schema exactly.

Input:
- category
- target_schema
- sources_master
- source_documents

Output:
- filled JSON only
```

## 13.2 Prompt B — 누락 필드 판정

역할:

* 어떤 필드가 비었는지, 최소 개수 미달인지 판정

```text
You are a schema completion validator.

Check the filled JSON against the category rules.
Mark fields as:
- complete
- partial
- missing

Rules:
- empty value = missing
- no sources = missing
- below minimum item count = partial
- vague unsupported wording = partial

Return:
{
  "missing_fields": [],
  "partial_fields": [],
  "field_scores": {},
  "completion_rate": 0.0
}
```

## 13.3 Prompt C — 재검색어 생성

역할:

* 누락 필드별 검색어 생성

```text
You are a research query generator.

Given category, topic, article title, current filled JSON, and missing fields,
generate targeted web search queries to fill only the missing fields.

Rules:
- Prefer factual search terms
- Include product, company, technology, pricing, examples, principle, expansion when relevant
- Avoid overly broad generic queries
- Return up to 3 queries per missing field
```

## 13.4 Prompt D — 보강 병합

역할:

* 추가 source를 반영해 기존 JSON 보강

```text
You are a structured evidence merger.

Merge new evidence into the current JSON.
Only update fields when the new sources provide stronger or additional evidence.
Keep prior valid values unless contradicted by higher-quality evidence.
If sources conflict, preserve a cautious merged statement and add notes.
```

## 13.5 Prompt E — 최종 검수

역할:

* 최종 품질 체크

```text
You are a final QA reviewer for structured research outputs.

Validate:
- schema integrity
- all source references exist
- no unsupported values
- required minimum counts
- notes only where needed

Return:
{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "final_completion_rate": 0.0
}
```

---

# 14. 카테고리별 좋은 결과 예시 기준

지금 당장 실데이터 예시가 없다면, 적어도 “좋은 결과가 무엇인지” 기준을 고정해야 한다.

## 14.1 해외 동향 좋은 결과 기준

* trend_name이 단순 기사 제목 복사가 아니라 실제 트렌드명
* definition이 한 줄로 명확함
* 기존 대비 변화가 “이전 → 현재” 흐름으로 설명됨
* 사례가 2개 이상
* 확산 방식이 지역 + 산업 확장 둘 다 언급됨

## 14.2 상품·서비스 좋은 결과 기준

* 제품명과 개발사 구분이 명확
* how_it_works가 기능 나열이 아니라 작동 방식 설명
* pricing/model 구분이 되어 있음
* differentiation이 일반 홍보문구가 아니라 비교 포인트를 담음

## 14.3 푸드테크 좋은 결과 기준

* 기술 원리가 실제 메커니즘 수준으로 설명됨
* 기존 방식의 문제와 해결이 짝으로 대응됨
* application과 use_case가 혼동되지 않음
* industry_meaning이 단순 “혁신적이다” 수준이 아님

---

# 15. DB 설계 권장안

기존 PRD의 ERD를 그대로 유지하면 된다. 핵심은 요청, 출처, 반복, 필드 상태, 결과 분리 저장이다. 

권장 핵심 테이블:

* `research_request`
* `article`
* `research_iteration`
* `search_query`
* `source_document`
* `field_status`
* `field_evidence`
* `research_result`

## 추가 컬럼 추천

`field_status`에 아래 2개 추가 추천:

* `is_required boolean`
* `min_items_required int`

`source_document`에 아래 2개 추가 추천:

* `domain varchar`
* `quality_tier varchar`

---

# 16. 구현용 내부 데이터 구조 추천

최종 응답 JSON 외에 내부적으로는 아래 구조를 두는 게 좋다.

## 16.1 FieldRule

```json
{
  "field_path": "cases",
  "required": true,
  "min_items": 2,
  "must_have_sources": true,
  "weight": 1.5
}
```

## 16.2 SearchTask

```json
{
  "request_id": "req_1",
  "iteration_no": 2,
  "field_path": "business_model.pricing",
  "queries": [
    "product pricing",
    "official pricing page",
    "subscription plan"
  ]
}
```

## 16.3 FieldEvidence

```json
{
  "field_path": "definition",
  "source_id": "S3",
  "evidence_text": "해당 기술은 ...",
  "evidence_score": 0.88
}
```

---

# 17. 권장 기술 스택

바이브 코딩 기준으로 너무 복잡하지 않게 가는 게 좋다.

## 추천

* API: FastAPI
* Worker: Celery 또는 Dramatiq
* DB: PostgreSQL + JSONB
* Cache/Queue: Redis
* Extraction: newspaper4k / trafilatura / readability fallback
* Search: SerpAPI류 또는 커스텀 검색 API
* LLM Orchestration: LangGraph까지는 optional, 초기엔 service class로 충분
* Validation: Pydantic
* Logging: structlog 또는 기본 JSON logging

## 초기 아키텍처

* `api/`
* `services/article_parser.py`
* `services/search_service.py`
* `services/extractor.py`
* `services/completion_engine.py`
* `services/result_merger.py`
* `services/validator.py`
* `repositories/`
* `workers/`

---

# 18. 개발 체크리스트

## 필수

* 카테고리 enum 고정
* target schema loader 구현
* field rule loader 구현
* article parser 구현
* search adapter 구현
* source deduper 구현
* extraction prompt 구현
* completion validator 구현
* iteration loop 구현
* result storage 구현

## 품질

* source 없는 값 차단
* 최소 개수 검증
* 동일 URL 중복 제거
* confidence threshold 적용
* timeout / retry
* partial_completed 허용 

---

# 19. 바로 코드로 옮길 때의 핵심 의사결정

이건 특히 중요하다.

## 고정해야 하는 것

1. 카테고리별 output schema
2. 카테고리별 field rules
3. completion_rate 기준
4. search source priority
5. 상태값/에러코드
6. notes 사용 원칙
7. source_id 매핑 방식

## 나중에 바꿔도 되는 것

1. 검색 API 공급자
2. extractor 라이브러리
3. worker 프레임워크
4. 동기/비동기 처리 비율
5. score 계산 세부 가중치

---

# 20. 최종 권장 운영 규칙

이 서비스는 아래 원칙만 지키면 품질이 많이 안정된다.

* **스키마 우선**
* **출처 없는 값 금지**
* **모르면 비워두기**
* **최소 개수 규칙 강제**
* **반복은 최대 3회**
* **partial_completed 허용**
* **검색은 누락 필드 중심으로 좁게**
* **공식 source 우선**
* **충돌 정보는 notes로 설명**
* **최종 반환 전 schema validation 필수**
