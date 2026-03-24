"""Endpoint response models."""
from typing import Any, Dict, List
from pydantic import BaseModel

from app.blog.schemas.outline import OutlineJSON
from app.blog.schemas.review import PipelineStatus, ReviewIssue


class GenerateOutlineResponse(BaseModel):
    status: PipelineStatus
    outline: OutlineJSON


class GenerateDraftResponse(BaseModel):
    status: PipelineStatus
    outline: OutlineJSON
    draft: str


class ReviewDraftResponse(BaseModel):
    status: PipelineStatus
    review_passed: bool
    issues: List[ReviewIssue]
    revised_draft: str


class GeneratePostResponse(BaseModel):
    status: PipelineStatus
    outline: OutlineJSON
    draft: str
    review_passed: bool
    issues: List[ReviewIssue]
    final_draft: str
    evidence_map: Dict[str, List[str]]
