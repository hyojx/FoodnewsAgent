from fastapi import APIRouter, HTTPException
from app.models.category_schemas import get_empty_schema, CATEGORY_SCHEMA_MAP
from app.config import SUPPORTED_CATEGORIES
from typing import Any, Dict

router = APIRouter(tags=["schemas"])


@router.get("/v1/schemas/{category}", response_model=Dict[str, Any])
def get_schema(category: str):
    if category not in SUPPORTED_CATEGORIES:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category}' not found. Supported: {SUPPORTED_CATEGORIES}",
        )
    return get_empty_schema(category)
