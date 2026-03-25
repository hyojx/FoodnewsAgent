import uuid
import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Any, Dict, Optional

from app.models.requests import (
    AdditionalResearchRequest,
    ResearchCreateRequest,
    ResearchCreateResponse,
    ResearchResultResponse,
    ResearchMeta,
    ResearchErrorDetail,
)
from app.repositories.research_repo import ResearchJob, get_repo
from app.services.research_orchestrator import ResearchOrchestrator

router = APIRouter(tags=["research"])


def _generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def _run_research_sync(job: ResearchJob) -> None:
    """Run research in background thread."""
    orchestrator = ResearchOrchestrator()
    orchestrator.process(job)


def _run_additional_sync(job: ResearchJob) -> None:
    """Run additional research in background thread."""
    orchestrator = ResearchOrchestrator()
    orchestrator.process_additional(job)


@router.post(
    "/v1/research",
    response_model=ResearchCreateResponse,
    status_code=202,
    summary="조사 요청 생성",
    description="""
새 리서치 작업을 생성하고 백그라운드에서 처리를 시작합니다.

**처리 흐름**: 기사 파싱 → LLM 1차 추출 → 누락 필드 탐지 → 재검색 반복 보강

결과는 즉시 반환되지 않습니다. 반환된 `request_id`로 `GET /v1/research/{request_id}`를 폴링하세요.

**지원 카테고리**: `해외 동향`, `상품·서비스`, `푸드테크`
""",
)
def create_research(
    request: ResearchCreateRequest,
    background_tasks: BackgroundTasks,
):
    repo = get_repo()
    request_id = _generate_request_id()

    job = ResearchJob(
        request_id=request_id,
        article_url=request.article_url,
        category=request.category,
        status="queued",
        options=request.options.model_dump(),
        target_schema=request.target_schema,
    )
    repo.create(job)

    background_tasks.add_task(_run_research_sync, job)

    return ResearchCreateResponse(request_id=request_id, status="queued")


@router.post(
    "/v1/research/additional",
    response_model=ResearchCreateResponse,
    status_code=202,
    summary="추가 리서치 요청",
    description="""
완료된 조사 결과에 자연어로 특정 정보를 추가 검색·보강합니다.

**입력 방식 (둘 중 하나 선택)**

- **request_id 방식**: 같은 서버 세션에 살아있는 기존 작업 ID를 전달
- **filled_schema 방식**: `filled_schema` + `article_url` + `category` 를 직접 전달
  (서버 재시작 후에도 사용 가능. `GET /v1/research/{id}` 응답의 `result.filled_schema` 값을 그대로 사용)

**검색 언어 자동 선택**: `filled_schema.sources_master[0].language` 기준
→ `en` → 영어/글로벌 검색, `ja` → 일본어 검색, `ko` → 한국어 검색

결과는 새 `request_id`로 `GET /v1/research/{request_id}` 폴링.
""",
)
def create_additional_research(
    request: AdditionalResearchRequest,
    background_tasks: BackgroundTasks,
):
    repo = get_repo()

    # Resolve filled_schema and metadata
    if request.request_id:
        existing_job = repo.get(request.request_id)
        if existing_job is None:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"Research job '{request.request_id}' not found. "
                       "In-memory jobs are lost on server restart — provide 'filled_schema' directly.",
            )
        filled_schema = existing_job.filled_schema or {}
        article_url = existing_job.article_url
        category = existing_job.category
    else:
        filled_schema = request.filled_schema or {}
        article_url = request.article_url or ""
        category = request.category or ""

    new_request_id = _generate_request_id()
    options = request.options.model_dump()
    options["additional_query"] = request.additional_query

    job = ResearchJob(
        request_id=new_request_id,
        article_url=article_url,
        category=category,
        status="queued",
        options=options,
        target_schema=filled_schema,
    )
    repo.create(job)

    background_tasks.add_task(_run_additional_sync, job)

    return ResearchCreateResponse(request_id=new_request_id, status="queued")


@router.get(
    "/v1/research/{request_id}",
    response_model=ResearchResultResponse,
    summary="조사 결과 조회",
    description="""
`request_id`로 조사 작업의 상태 및 결과를 조회합니다.

**status 값**
- `queued` — 대기 중
- `processing` — 처리 중
- `completed` — 목표 completion_rate 달성 (≥ 0.85)
- `partial_completed` — 일부 필드 누락이나 반환 가능한 수준 (≥ 0.60)
- `failed` — 치명적 오류 또는 품질 미달

작업이 완료되면 `result.filled_schema`에 구조화된 조사 결과 JSON이 담깁니다.
""",
)
def get_research(request_id: str):
    repo = get_repo()
    job = repo.get(request_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Research job '{request_id}' not found")

    meta = ResearchMeta(
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        sources_used=job.sources_used,
    )

    error = None
    if job.error_code:
        error = ResearchErrorDetail(code=job.error_code, message=job.error_message or "")

    result = None
    if job.filled_schema is not None:
        result = {
            "filled_schema": job.filled_schema,
            "missing_fields": job.missing_fields,
            "sources_used": job.sources_used,
        }

    return ResearchResultResponse(
        request_id=job.request_id,
        status=job.status,
        category=job.category,
        article_url=job.article_url,
        completion_rate=job.completion_rate if job.filled_schema else None,
        iterations_count=job.iterations_count if job.iterations_count > 0 else None,
        missing_fields=job.missing_fields if job.filled_schema else None,
        result=result,
        meta=meta,
        error=error,
    )
