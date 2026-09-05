"""Agent schemas — registration, health, capabilities."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class AgentCapability(BaseModel):
    """A single named capability an agent advertises."""
    name: str
    description: str = ""
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None
    version: str = "1.0"


class AgentRegistration(BaseModel):
    """Payload sent by an agent when it registers with the registry."""
    agent_id: str = Field(..., description="Globally unique agent identifier, e.g. 'news-verifier'")
    name: str
    description: str = ""
    version: str = "1.0.0"
    host: str
    port: int
    capabilities: list[str] = Field(default_factory=list)
    capability_details: list[AgentCapability] = Field(default_factory=list)
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None
    required_permissions: list[str] = Field(default_factory=list)
    cost_estimate: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentInfo(AgentRegistration):
    """Full agent record returned by the registry."""
    status: str = "initializing"
    reliability_score: float = 1.0
    avg_latency_ms: Optional[float] = None
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentHealthReport(BaseModel):
    """Heartbeat / health data submitted by an agent."""
    agent_id: str
    status: str  # healthy | degraded | unhealthy
    latency_ms: Optional[float] = None
    error_rate: Optional[float] = None
    success_rate: Optional[float] = None
    queue_depth: Optional[int] = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
