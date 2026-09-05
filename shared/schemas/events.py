"""Event bus schemas — versioned event envelope."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventVersion(str):
    """Simple semantic version string for event schemas."""
    pass


class BaseEvent(BaseModel):
    """
    All RabbitMQ events must use this envelope.
    Ensures trace context, versioning and tenant isolation are always present.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str  # e.g. "news.article.ingested"
    event_version: str = "1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str = "default"
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    producer: str = ""
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


# -------------------------------------------------------------------------
# Typed event sub-classes for each event type
# -------------------------------------------------------------------------

class TaskCreatedEvent(BaseEvent):
    event_type: str = "task.created"


class TaskCompletedEvent(BaseEvent):
    event_type: str = "task.completed"


class TaskFailedEvent(BaseEvent):
    event_type: str = "task.failed"


class AgentRegisteredEvent(BaseEvent):
    event_type: str = "agent.registered"


class AgentHeartbeatEvent(BaseEvent):
    event_type: str = "agent.heartbeat"


class AgentUnhealthyEvent(BaseEvent):
    event_type: str = "agent.unhealthy"


class NewsArticleIngestedEvent(BaseEvent):
    event_type: str = "news.article.ingested"


class NewsEventUpdatedEvent(BaseEvent):
    event_type: str = "news.event.updated"


class NewsClaimExtractedEvent(BaseEvent):
    event_type: str = "news.claim.extracted"


class NewsVerificationRequestedEvent(BaseEvent):
    event_type: str = "news.verification.requested"


class NewsVerificationCompletedEvent(BaseEvent):
    event_type: str = "news.verification.completed"


class EvidenceCreatedEvent(BaseEvent):
    event_type: str = "evidence.created"


class HumanReviewRequiredEvent(BaseEvent):
    event_type: str = "human.review_required"


class HumanApprovedEvent(BaseEvent):
    event_type: str = "human.approved"


class HumanRejectedEvent(BaseEvent):
    event_type: str = "human.rejected"


class WorkflowStartedEvent(BaseEvent):
    event_type: str = "workflow.started"


class WorkflowCompletedEvent(BaseEvent):
    event_type: str = "workflow.completed"


class WorkflowFailedEvent(BaseEvent):
    event_type: str = "workflow.failed"
