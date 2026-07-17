"""Liveness API endpoints."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service liveness")
async def health_check() -> HealthResponse:
    """Confirm that the API process can serve requests.

    Dependency readiness checks will be added separately so a temporary
    database outage does not cause the application process to restart-loop.
    """

    return HealthResponse(status="ok", service=settings.app_name, version="v1")
