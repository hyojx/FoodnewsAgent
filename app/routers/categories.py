from fastapi import APIRouter
from app.models.requests import CategoriesResponse
from app.config import SUPPORTED_CATEGORIES

router = APIRouter(tags=["categories"])


@router.get("/v1/categories", response_model=CategoriesResponse)
def list_categories():
    return CategoriesResponse(categories=SUPPORTED_CATEGORIES)
