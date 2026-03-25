from fastapi import APIRouter
from app.models.requests import CategoriesResponse
from app.config import SUPPORTED_CATEGORIES

router = APIRouter(tags=["categories"])


@router.get(
    "/v1/categories",
    response_model=CategoriesResponse,
    summary="지원 카테고리 목록 조회",
    description="사용 가능한 조사 카테고리 목록을 반환합니다. `POST /v1/research`의 `category` 파라미터에 사용하세요.",
)
def list_categories():
    return CategoriesResponse(categories=SUPPORTED_CATEGORIES)
