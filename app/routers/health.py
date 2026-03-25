from fastapi import APIRouter
from app.models.requests import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="헬스체크")
def health_check():
    return HealthResponse(status="ok")
