from typing import Any, Dict, List, Optional
from pydantic import BaseModel, HttpUrl, Field, field_validator, model_validator

from app.config import SUPPORTED_CATEGORIES


class ResearchOptions(BaseModel):
    max_iterations: int = Field(3, ge=1, le=20, description="최대 반복 검색 횟수 (1~20)")
    min_completion_rate: float = Field(0.85, ge=0.0, le=1.0, description="목표 완성도 (0.0~1.0). 이 값 이상이면 completed 처리")
    locale: str = Field("ko-KR", description="로케일 설정")
    search_limit_per_iteration: int = Field(5, description="반복당 최대 검색 결과 수")

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
    article_url: str = Field(..., description="조사할 원문 기사 URL (http:// 또는 https://)")
    category: str = Field(..., description=f"조사 카테고리. 지원 값: {SUPPORTED_CATEGORIES}")
    target_schema: Optional[Dict[str, Any]] = Field(None, description="사전 입력된 스키마 (선택). 없으면 카테고리 기본 스키마 사용")
    options: ResearchOptions = Field(default_factory=ResearchOptions, description="조사 옵션")

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


class AdditionalResearchRequest(BaseModel):
    """완료된 조사 결과에 추가 정보를 검색·보강하는 요청.

    **입력 방식 (둘 중 하나 필수)**
    - `request_id`: 같은 서버 세션의 기존 작업 ID
    - `filled_schema` + `article_url` + `category`: 직접 JSON 전달
    """
    request_id: Optional[str] = Field(None, description="기존 조사 작업 ID. 서버 재시작 시 무효화됨")
    filled_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="기존 조사 결과 JSON. GET /v1/research/{id} 응답의 result.filled_schema 값을 그대로 사용"
    )
    article_url: Optional[str] = Field(None, description="원문 기사 URL. filled_schema 방식 사용 시 필수")
    category: Optional[str] = Field(None, description=f"조사 카테고리. filled_schema 방식 사용 시 필수. 지원 값: {SUPPORTED_CATEGORIES}")
    additional_query: str = Field(..., description="추가로 조사할 내용을 자연어로 입력 (예: '이 제품의 가격 정보와 경쟁사 비교가 필요해')")
    options: ResearchOptions = Field(default_factory=ResearchOptions, description="조사 옵션")

    @model_validator(mode="after")
    def validate_source(self) -> "AdditionalResearchRequest":
        has_id = self.request_id is not None
        has_schema = self.filled_schema is not None
        if not has_id and not has_schema:
            raise ValueError("Provide either 'request_id' or 'filled_schema' (with 'article_url' and 'category')")
        if has_schema:
            if not self.article_url:
                raise ValueError("'article_url' is required when providing 'filled_schema'")
            if not self.article_url.startswith(("http://", "https://")):
                raise ValueError("article_url must start with http:// or https://")
            if not self.category:
                raise ValueError("'category' is required when providing 'filled_schema'")
            if self.category not in SUPPORTED_CATEGORIES:
                raise ValueError(f"Unsupported category '{self.category}'. Supported: {SUPPORTED_CATEGORIES}")
        if not self.additional_query.strip():
            raise ValueError("'additional_query' must not be empty")
        return self


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
