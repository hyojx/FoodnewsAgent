"""Review result schema and pipeline status enum."""
from enum import Enum
from typing import List
from pydantic import BaseModel


class PipelineStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    NORMALIZED = "NORMALIZED"
    OUTLINE_CREATED = "OUTLINE_CREATED"
    DRAFT_CREATED = "DRAFT_CREATED"
    REVIEW_FAILED = "REVIEW_FAILED"
    REVIEW_PASSED = "REVIEW_PASSED"
    FINALIZED = "FINALIZED"


class IssueType(str, Enum):
    UNSUPPORTED_CLAIM = "unsupported_claim"
    FORBIDDEN_EXPRESSION = "forbidden_expression"
    MISSING_SECTION = "missing_section"
    DEFINITIVE_IMPLICATION = "definitive_implication"
    READABILITY = "readability"
    TONE_VIOLATION = "tone_violation"


class ReviewIssue(BaseModel):
    type: str
    text: str
    reason: str


class ReviewResult(BaseModel):
    """
    Wraps the LLM review output.
    The LLM returns {"pass": ..., "issues": ..., "revised_draft": ...}.
    We parse "pass" into `passed` to avoid Python keyword collision.
    """
    passed: bool
    issues: List[ReviewIssue]
    revised_draft: str
