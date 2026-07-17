"""Health endpoint response schemas."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Public liveness response."""

    status: Literal["ok"] = "ok"
    service: str
    version: str
