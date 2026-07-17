"""Version 1 API composition root."""

from fastapi import APIRouter

from app.api.v1.assistant import router as assistant_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.workflows import router as workflows_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(knowledge_router)
api_router.include_router(assistant_router)
api_router.include_router(workflows_router)
