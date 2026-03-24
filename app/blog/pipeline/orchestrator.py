"""BlogPipeline — orchestrates the 3-agent pipeline with status tracking."""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.blog.pipeline.generate import OutlineGenerator, DraftWriter
from app.blog.pipeline.review import ReviewAgent
from app.blog.schemas.outline import OutlineJSON
from app.blog.schemas.review import PipelineStatus, ReviewResult
from app.blog.schemas.response import GeneratePostResponse


@dataclass
class PipelineState:
    status: PipelineStatus = PipelineStatus.EXTRACTED
    outline: OutlineJSON | None = None
    draft: str = ""
    review: ReviewResult | None = None
    final_draft: str = ""


class BlogPipeline:
    """
    Executes: normalized JSON → outline → draft → review → final output.
    Tracks pipeline status through all 7 states.
    """

    def __init__(self) -> None:
        self._outline_gen = OutlineGenerator()
        self._draft_writer = DraftWriter()
        self._review_agent = ReviewAgent()

    def run(self, article_json: Dict[str, Any]) -> GeneratePostResponse:
        state = PipelineState(status=PipelineStatus.NORMALIZED)

        # Stage 1: Generate outline
        outline = self._outline_gen.generate(article_json)
        state.outline = outline
        state.status = PipelineStatus.OUTLINE_CREATED

        # Stage 2: Write draft
        draft = self._draft_writer.write(article_json, outline)
        state.draft = draft
        state.status = PipelineStatus.DRAFT_CREATED

        # Stage 3: Review and revise
        review = self._review_agent.review(article_json, outline, draft)
        state.review = review

        if review.passed:
            state.status = PipelineStatus.REVIEW_PASSED
        else:
            state.status = PipelineStatus.REVIEW_FAILED

        state.final_draft = review.revised_draft or draft
        state.status = PipelineStatus.FINALIZED

        return GeneratePostResponse(
            status=state.status,
            outline=outline,
            draft=draft,
            review_passed=review.passed,
            issues=review.issues,
            final_draft=state.final_draft,
            evidence_map=outline.evidence_map,
        )
