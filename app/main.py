from fastapi import FastAPI
from app.routers import health, research, schemas, categories
from app.blog.api.router import router as blog_router

app = FastAPI(
    title="IRA API — Iterative Research Agent",
    description="""
## 개요

원문 기사 URL과 카테고리를 입력받아, 관련 자료를 반복 검색·수집·분석하여 목표 JSON 스키마를 채운 뒤 구조화된 조사 결과를 반환하는 리서치 에이전트 API.

## 처리 흐름

1. `POST /v1/research` 로 조사 요청 → `request_id` 즉시 반환
2. 백그라운드에서 기사 파싱 → LLM 추출 → 누락 필드 탐지 → 재검색 반복
3. `GET /v1/research/{request_id}` 로 상태 및 결과 폴링

## 추가 리서치

완료된 조사 결과에 자연어로 특정 정보를 추가 요청할 수 있다.

- `POST /v1/research/additional` — 기존 `request_id` 또는 `filled_schema` JSON과 함께 `additional_query` 전달
- 검색 언어는 원문 기사 언어(`sources_master[0].language`)를 기준으로 자동 선택 (영어·일본어·한국어·중국어 지원)

## 지원 카테고리

- `해외 동향` — 해외 식품 트렌드 분석
- `상품·서비스` — 식품 관련 상품·서비스 분석
- `푸드테크` — 식품 기술 분석
""",
    version="1.1.0",
)

app.include_router(health.router)
app.include_router(research.router)
app.include_router(schemas.router)
app.include_router(categories.router)
app.include_router(blog_router)
