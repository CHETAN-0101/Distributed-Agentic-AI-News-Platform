"""Workflow schemas — DAG definition and state."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATING = "compensating"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_APPROVAL = "awaiting_approval"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowNode(BaseModel):
    """A single node in the workflow DAG."""
    node_id: str = Field(default_factory=lambda: str(uuid4()))
    capability: str
    agent_id: Optional[str] = None  # resolved at runtime
    depends_on: list[str] = Field(default_factory=list)
    input_mapping: dict[str, Any] = Field(default_factory=dict)
    output_key: Optional[str] = None
    status: NodeStatus = NodeStatus.PENDING
    max_retries: int = 3
    timeout_seconds: Optional[int] = None
    requires_approval: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowGraph(BaseModel):
    """The complete workflow DAG."""
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[tuple[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowCreate(BaseModel):
    """Payload to create a new workflow."""
    name: str
    description: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    graph: Optional[WorkflowGraph] = None
    goal: Optional[str] = None  # Let the planner build the graph
    priority: str = "NORMAL"
    deadline: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    tenant_id: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Workflow record returned by API."""
    id: str
    tenant_id: str
    name: str
    description: str
    status: WorkflowStatus
    priority: str
    graph: dict[str, Any]
    input: Optional[dict[str, Any]]
    output: Optional[dict[str, Any]]
    error: Optional[dict[str, Any]]
    trace_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
