from fastapi import APIRouter, HTTPException
from app.models.category_schemas import get_empty_schema, CATEGORY_SCHEMA_MAP
from app.config import SUPPORTED_CATEGORIES, normalize_category
from typing import Any, Dict

router = APIRouter(tags=["schemas"])


@router.get(
    "/v1/schemas/{category}",
    response_model=Dict[str, Any],
    summary="카테고리별 빈 스키마 조회",
    description="""
해당 카테고리의 빈 JSON 스키마 템플릿을 반환합니다.

**지원 카테고리**: `해외 동향`, `상품·서비스`, `푸드테크`

`POST /v1/research`의 `target_schema` 파라미터에 활용하거나,
`POST /v1/research/additional`의 `filled_schema` 구조 참고용으로 사용할 수 있습니다.
""",
)
def get_schema(category: str):
    canonical = normalize_category(category)
    if canonical is None:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category}' not found. Supported: {SUPPORTED_CATEGORIES}",
        )
    return get_empty_schema(canonical)
