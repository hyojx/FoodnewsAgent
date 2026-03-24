import uuid
import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Any, Dict, Optional

from app.models.requests import (
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


@router.post("/v1/research", response_model=ResearchCreateResponse, status_code=202)
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


@router.get("/v1/research/{request_id}", response_model=ResearchResultResponse)
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
