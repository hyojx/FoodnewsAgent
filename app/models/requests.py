from typing import Any, Dict, List, Optional
from pydantic import BaseModel, HttpUrl, field_validator

from app.config import SUPPORTED_CATEGORIES


class ResearchOptions(BaseModel):
    max_iterations: int = 3
    min_completion_rate: float = 0.85
    locale: str = "ko-KR"
    search_limit_per_iteration: int = 5

    @field_validator("max_iterations")
    @classmethod
    def validate_max_iterations(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("max_iterations must be between 1 and 20")
        return v

    @field_validator("min_completion_rate")
    @classmethod
    def validate_completion_rate(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("min_completion_rate must be between 0.0 and 1.0")
        return v


class ResearchCreateRequest(BaseModel):
    article_url: str
    category: str
    target_schema: Optional[Dict[str, Any]] = None
    options: ResearchOptions = ResearchOptions()

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in SUPPORTED_CATEGORIES:
            raise ValueError(f"Unsupported category '{v}'. Supported: {SUPPORTED_CATEGORIES}")
        return v

    @field_validator("article_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("article_url must start with http:// or https://")
        return v


class ResearchCreateResponse(BaseModel):
    request_id: str
    status: str


class ResearchErrorDetail(BaseModel):
    code: str
    message: str


class ResearchMeta(BaseModel):
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    sources_used: int = 0


class ResearchResultResponse(BaseModel):
    request_id: str
    status: str
    category: Optional[str] = None
    article_url: Optional[str] = None
    completion_rate: Optional[float] = None
    iterations_count: Optional[int] = None
    missing_fields: Optional[List[str]] = None
    result: Optional[Dict[str, Any]] = None
    meta: Optional[ResearchMeta] = None
    error: Optional[ResearchErrorDetail] = None


class CategoriesResponse(BaseModel):
    categories: List[str]


class HealthResponse(BaseModel):
    status: str
