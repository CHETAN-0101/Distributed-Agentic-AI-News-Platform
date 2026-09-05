"""Common utility schemas."""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1


class HealthResponse(BaseModel):
    status: str  # healthy | degraded | unhealthy
    service: str
    version: str = "0.1.0"
    checks: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    trace_id: Optional[str] = None
