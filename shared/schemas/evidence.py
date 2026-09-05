"""
Evidence and claim schemas.
Every meaningful generated conclusion must be traceable.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    OBSERVATION = "OBSERVATION"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    SUPPORTED_FACT = "SUPPORTED_FACT"
    CONFLICTING_CLAIM = "CONFLICTING_CLAIM"
    UNVERIFIED_CLAIM = "UNVERIFIED_CLAIM"


class ClaimStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    SUPPORTED = "SUPPORTED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    OPINION = "OPINION"
    CORRECTED = "CORRECTED"
    OUTDATED = "OUTDATED"


class EvidenceItem(BaseModel):
    """A single piece of evidence attached to a claim or task result."""
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    evidence_type: EvidenceType
    content: str
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    passage: Optional[str] = None  # exact relevant excerpt
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    credibility: Optional[float] = Field(None, ge=0.0, le=1.0)
    agent_id: Optional[str] = None
    model_used: Optional[str] = None
    task_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Claim(BaseModel):
    """An extracted factual claim from an article or task."""
    claim_id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: Optional[str] = None
    article_id: Optional[str] = None
    text: str
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    source_agent_id: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
