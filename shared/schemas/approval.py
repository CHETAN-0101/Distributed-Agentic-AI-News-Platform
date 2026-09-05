"""Approval request schemas — human-in-the-loop."""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalRequest(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "default"
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    requested_by: str
    action: str
    risk_level: RiskLevel
    reason: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    proposed_change: Optional[dict[str, Any]] = None
    rollback_plan: Optional[dict[str, Any]] = None
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=24)
    )
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalDecision(BaseModel):
    approval_id: str
    decision: str  # approved | rejected
    reviewer_id: str
    reviewer_note: Optional[str] = None
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
