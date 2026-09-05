"""News domain schemas — articles, events, verification states."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class NewsVerificationState(str, Enum):
    CONFIRMED = "CONFIRMED"
    SUPPORTED = "SUPPORTED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    OPINION = "OPINION"
    CORRECTED = "CORRECTED"
    OUTDATED = "OUTDATED"


class NamedEntity(BaseModel):
    text: str
    label: str  # PERSON, ORG, GPE, DATE, etc.
    confidence: float = 1.0


class NewsArticle(BaseModel):
    """Normalized news article — output of the ingestion agent."""
    article_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    content: str
    summary: Optional[str] = None
    source: str
    source_type: str = "news"  # official | news | institutional | social | rss
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    url: str
    language: str = "en"
    category: Optional[str] = None
    entities: list[NamedEntity] = Field(default_factory=list)
    word_count: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class TimelineEntry(BaseModel):
    timestamp: datetime
    title: str
    description: str
    source: Optional[str] = None
    article_id: Optional[str] = None
    entry_type: str = "update"  # initial | update | official | correction | clarification


class NewsEvent(BaseModel):
    """A story cluster — multiple articles covering the same real-world event."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: Optional[str] = None
    status: str = "developing"
    category: Optional[str] = None
    importance: float = Field(0.5, ge=0.0, le=1.0)
    entities: list[NamedEntity] = Field(default_factory=list)
    article_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NewsSummary(BaseModel):
    """Structured news summary — output of the summary agent."""
    event_id: str
    summary_type: str  # brief_30s | brief_60s | deep
    what_happened: str
    confirmed: list[str] = Field(default_factory=list)
    conflicting: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    why_it_matters: str = ""
    sources: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    confidence: float = 0.5
    generated_at: datetime = Field(default_factory=datetime.utcnow)
