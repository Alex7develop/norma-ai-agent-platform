"""Version 1 API composition root."""

from fastapi import APIRouter

from app.api.v1.assistant import router as assistant_router
from app.api.v1.health import router as health_router
from app.api.v1.knowledge import router as knowledge_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(knowledge_router)
api_router.include_router(assistant_router)
