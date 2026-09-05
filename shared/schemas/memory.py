"""Memory schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EVIDENCE = "evidence"
    REFLECTION = "reflection"


class MemoryEntry(BaseModel):
    memory_type: MemoryType
    content: str
    key: Optional[str] = None
    agent_id: Optional[str] = None
    tenant_id: str = "default"
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    importance: float = Field(0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_task_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class MemoryQuery(BaseModel):
    query: str
    tenant_id: str = "default"
    agent_id: Optional[str] = None
    memory_types: list[MemoryType] = Field(default_factory=list)
    top_k: int = 10
    min_score: float = 0.0


class MemoryResult(BaseModel):
    memory_id: str
    memory_type: MemoryType
    content: str
    score: float
    confidence: float
    importance: float
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
