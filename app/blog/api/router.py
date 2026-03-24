"""Blog generation API — 4 endpoints as defined in addpipeline.md."""
from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.blog.schemas.article import ArticleInput
from app.blog.schemas.outline import OutlineJSON
from app.blog.schemas.response import (
    GenerateOutlineResponse,
    GenerateDraftResponse,
    ReviewDraftResponse,
    GeneratePostResponse,
)
from app.blog.schemas.review import PipelineStatus
from app.blog.pipeline.generate import OutlineGenerator, DraftWriter
from app.blog.pipeline.review import ReviewAgent
from app.blog.pipeline.orchestrator import BlogPipeline

router = APIRouter(tags=["blog"])


# ─── Request bodies ────────────────────────────────────────────────────────────

class GenerateOutlineRequest(ArticleInput):
    pass


class GenerateDraftRequest(BaseModel):
    article_json: Dict[str, Any]
    outline: OutlineJSON


class ReviewDraftRequest(BaseModel):
    article_json: Dict[str, Any]
    outline: OutlineJSON
    draft: str


class GeneratePostRequest(ArticleInput):
    pass


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate-outline", response_model=GenerateOutlineResponse)
def generate_outline(request: GenerateOutlineRequest) -> GenerateOutlineResponse:
    """Agent 1: Generate outline from normalized article JSON."""
    generator = OutlineGenerator()
    outline = generator.generate(request.article_json)
    return GenerateOutlineResponse(
        status=PipelineStatus.OUTLINE_CREATED,
        outline=outline,
    )


@router.post("/generate-draft", response_model=GenerateDraftResponse)
def generate_draft(request: GenerateDraftRequest) -> GenerateDraftResponse:
    """Agent 2: Generate draft from outline + article JSON."""
    writer = DraftWriter()
    draft = writer.write(request.article_json, request.outline)
    return GenerateDraftResponse(
        status=PipelineStatus.DRAFT_CREATED,
        outline=request.outline,
        draft=draft,
    )


@router.post("/review-draft", response_model=ReviewDraftResponse)
def review_draft(request: ReviewDraftRequest) -> ReviewDraftResponse:
    """Agent 3: Review draft for factuality, structure, tone, and readability."""
    agent = ReviewAgent()
    result = agent.review(request.article_json, request.outline, request.draft)
    status = PipelineStatus.REVIEW_PASSED if result.passed else PipelineStatus.REVIEW_FAILED
    return ReviewDraftResponse(
        status=status,
        review_passed=result.passed,
        issues=result.issues,
        revised_draft=result.revised_draft,
    )


@router.post("/generate-post", response_model=GeneratePostResponse)
def generate_post(request: GeneratePostRequest) -> GeneratePostResponse:
    """Full pipeline: normalized JSON → outline → draft → review → finalized post."""
    pipeline = BlogPipeline()
    return pipeline.run(request.article_json)
