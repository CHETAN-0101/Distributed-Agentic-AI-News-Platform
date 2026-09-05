"""Task schemas — the core agent contract (input + output)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskInput(BaseModel):
    """
    Standard input envelope for any agent task.
    This is the universal agent contract input — all agents receive this.
    """
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: Optional[str] = None
    workflow_node_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    tenant_id: str = "default"
    agent_id: str = ""
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    deadline: Optional[datetime] = None
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    max_retries: int = 3
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Optional[float] = None


class EvidenceRef(BaseModel):
    evidence_id: str
    source: str
    passage: Optional[str] = None
    confidence: float = 0.5


class TaskOutput(BaseModel):
    """
    Standard output envelope for any agent task.
    This is the universal agent contract output — all agents produce this.
    """
    task_id: str
    agent_id: str
    status: TaskStatus
    result: dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    execution_time_ms: Optional[int] = None
    token_usage: Optional[TokenUsage] = None
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
