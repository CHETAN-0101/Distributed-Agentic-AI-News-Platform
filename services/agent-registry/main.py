"""
AgentOS — Agent Registry Service
Handles agent registration, discovery, health tracking, and circuit breaker state.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter, Gauge
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from shared.config import settings
from shared.logging import configure_logging, get_logger
from shared.schemas.agent import AgentInfo, AgentRegistration, AgentHealthReport, CircuitBreakerState
from shared.schemas.common import HealthResponse, PaginatedResponse, ErrorResponse
from shared.tracing import configure_tracing, instrument_fastapi

configure_logging(service_name="agent-registry", log_level=settings.log_level)
configure_tracing(service_name="agent-registry")

logger = get_logger(__name__)

# -------------------------------------------------------------------------
# Database
# -------------------------------------------------------------------------
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.is_development,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# -------------------------------------------------------------------------
# Metrics
# -------------------------------------------------------------------------
agents_registered = Gauge("agentos_agents_registered_total", "Total registered agents")
agents_healthy = Gauge("agentos_agents_healthy", "Healthy agents count")
agents_unhealthy = Gauge("agentos_agents_unhealthy", "Unhealthy agents count")
registrations_total = Counter("agentos_agent_registrations_total", "Total registration requests")

# -------------------------------------------------------------------------
# In-memory agent store (production would rely purely on Postgres)
# -------------------------------------------------------------------------
_agent_store: dict[str, AgentInfo] = {}
UNHEALTHY_THRESHOLD_SECONDS = 90  # mark unhealthy if no heartbeat for 90s
CIRCUIT_OPEN_FAILURES = 5


# -------------------------------------------------------------------------
# App Lifecycle
# -------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Agent Registry starting")
    # Start background health monitor
    monitor_task = asyncio.create_task(_health_monitor_loop())
    yield
    monitor_task.cancel()
    await engine.dispose()
    logger.info("Agent Registry stopped")


app = FastAPI(
    title="AgentOS — Agent Registry",
    description="Central registry for all AgentOS agents. Handles registration, discovery, health, and circuit breaker state.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

instrument_fastapi(app)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# -------------------------------------------------------------------------
# Health
# -------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        service="agent-registry",
        checks={
            "database": "ok" if db_ok else "error",
            "registered_agents": len(_agent_store),
        },
    )


@app.get("/readiness", tags=["system"])
async def readiness():
    return {"status": "ready"}


# -------------------------------------------------------------------------
# Agent Registration & Discovery
# -------------------------------------------------------------------------
@app.post(
    "/agents/register",
    response_model=AgentInfo,
    status_code=status.HTTP_201_CREATED,
    tags=["agents"],
    summary="Register or update an agent",
)
async def register_agent(registration: AgentRegistration):
    """
    Called by agents on startup. Idempotent — updates existing registration.
    """
    registrations_total.inc()

    now = datetime.utcnow()

    if registration.agent_id in _agent_store:
        # Update existing
        existing = _agent_store[registration.agent_id]
        agent_info = AgentInfo(
            **registration.model_dump(),
            status="healthy",
            reliability_score=existing.reliability_score,
            avg_latency_ms=existing.avg_latency_ms,
            circuit_breaker_state=existing.circuit_breaker_state,
            last_heartbeat=now,
            registered_at=existing.registered_at,
            updated_at=now,
        )
        logger.info("Agent re-registered", agent_id=registration.agent_id)
    else:
        agent_info = AgentInfo(
            **registration.model_dump(),
            status="healthy",
            last_heartbeat=now,
            registered_at=now,
            updated_at=now,
        )
        logger.info("Agent registered", agent_id=registration.agent_id, capabilities=registration.capabilities)

    _agent_store[registration.agent_id] = agent_info
    _update_metrics()

    # Persist to DB (fire-and-forget)
    asyncio.create_task(_persist_agent(agent_info))

    return agent_info


@app.get(
    "/agents",
    response_model=PaginatedResponse[AgentInfo],
    tags=["agents"],
    summary="List all registered agents",
)
async def list_agents(
    status_filter: Optional[str] = Query(None, alias="status"),
    capability: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    agents = list(_agent_store.values())

    if status_filter:
        agents = [a for a in agents if a.status == status_filter]
    if capability:
        agents = [a for a in agents if capability in a.capabilities]

    total = len(agents)
    start = (page - 1) * page_size
    items = agents[start: start + page_size]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@app.get(
    "/agents/{agent_id}",
    response_model=AgentInfo,
    tags=["agents"],
    summary="Get a specific agent by ID",
)
async def get_agent(agent_id: str):
    agent = _agent_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return agent


@app.delete(
    "/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["agents"],
    summary="Deregister an agent",
)
async def deregister_agent(agent_id: str):
    if agent_id not in _agent_store:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    del _agent_store[agent_id]
    _update_metrics()
    logger.info("Agent deregistered", agent_id=agent_id)


# -------------------------------------------------------------------------
# Discovery
# -------------------------------------------------------------------------
@app.get(
    "/agents/discover/{capability}",
    response_model=list[AgentInfo],
    tags=["discovery"],
    summary="Find healthy agents for a capability",
)
async def discover_agents_by_capability(
    capability: str,
    min_reliability: float = Query(0.0, ge=0.0, le=1.0),
):
    """
    Find healthy agents with the given capability.
    Results sorted by: reliability × (1 - error_rate) - latency penalty.
    """
    candidates = [
        a for a in _agent_store.values()
        if capability in a.capabilities
        and a.status in ("healthy", "degraded")
        and a.circuit_breaker_state != CircuitBreakerState.OPEN
        and a.reliability_score >= min_reliability
    ]

    def score(agent: AgentInfo) -> float:
        latency_penalty = (agent.avg_latency_ms or 1000) / 10000
        return agent.reliability_score - latency_penalty

    return sorted(candidates, key=score, reverse=True)


# -------------------------------------------------------------------------
# Heartbeat & Health
# -------------------------------------------------------------------------
@app.post(
    "/agents/{agent_id}/heartbeat",
    response_model=AgentInfo,
    tags=["health"],
    summary="Submit agent health report",
)
async def agent_heartbeat(agent_id: str, report: AgentHealthReport):
    agent = _agent_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not registered")

    agent.last_heartbeat = datetime.utcnow()
    agent.status = report.status
    agent.updated_at = datetime.utcnow()

    if report.latency_ms is not None:
        # Exponential moving average for latency
        prev = agent.avg_latency_ms or report.latency_ms
        agent.avg_latency_ms = 0.8 * prev + 0.2 * report.latency_ms

    if report.success_rate is not None:
        agent.reliability_score = 0.9 * agent.reliability_score + 0.1 * report.success_rate

    # Auto-close circuit breaker on healthy heartbeat
    if agent.circuit_breaker_state == CircuitBreakerState.HALF_OPEN and report.status == "healthy":
        agent.circuit_breaker_state = CircuitBreakerState.CLOSED
        logger.info("Circuit breaker closed", agent_id=agent_id)

    _update_metrics()
    return agent


@app.post(
    "/agents/{agent_id}/circuit-breaker/{state}",
    response_model=AgentInfo,
    tags=["health"],
    summary="Manually set circuit breaker state",
)
async def set_circuit_breaker(agent_id: str, state: CircuitBreakerState):
    agent = _agent_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    agent.circuit_breaker_state = state
    agent.updated_at = datetime.utcnow()
    logger.info("Circuit breaker updated", agent_id=agent_id, state=state)
    return agent


# -------------------------------------------------------------------------
# Background health monitor
# -------------------------------------------------------------------------
async def _health_monitor_loop() -> None:
    """
    Periodically mark agents as unhealthy if they miss heartbeats.
    Implements the circuit breaker open→half-open transition.
    """
    while True:
        await asyncio.sleep(30)
        now = datetime.utcnow()
        threshold = now - timedelta(seconds=UNHEALTHY_THRESHOLD_SECONDS)

        for agent in _agent_store.values():
            if agent.last_heartbeat and agent.last_heartbeat < threshold:
                if agent.status != "offline":
                    agent.status = "unhealthy"
                    logger.warning("Agent missed heartbeat", agent_id=agent.agent_id)

                    # Open circuit breaker
                    if agent.circuit_breaker_state == CircuitBreakerState.CLOSED:
                        agent.circuit_breaker_state = CircuitBreakerState.OPEN
                        logger.warning("Circuit breaker opened", agent_id=agent.agent_id)

            # Transition OPEN → HALF_OPEN after 2 minutes
            elif agent.circuit_breaker_state == CircuitBreakerState.OPEN:
                if agent.last_heartbeat and agent.last_heartbeat > now - timedelta(seconds=120):
                    agent.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker half-open", agent_id=agent.agent_id)

        _update_metrics()


def _update_metrics() -> None:
    agents_registered.set(len(_agent_store))
    healthy = sum(1 for a in _agent_store.values() if a.status == "healthy")
    unhealthy = sum(1 for a in _agent_store.values() if a.status in ("unhealthy", "offline"))
    agents_healthy.set(healthy)
    agents_unhealthy.set(unhealthy)


async def _persist_agent(agent_info: AgentInfo) -> None:
    """Persist agent record to PostgreSQL (upsert)."""
    try:
        async with SessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO agents (
                        agent_id, name, description, version, status, host, port,
                        capabilities, required_permissions, metadata,
                        reliability_score, avg_latency_ms, cost_estimate,
                        last_heartbeat, registered_at, created_at, updated_at
                    ) VALUES (
                        :agent_id, :name, :description, :version, :status, :host, :port,
                        :capabilities, :required_permissions, :metadata,
                        :reliability_score, :avg_latency_ms, :cost_estimate,
                        :last_heartbeat, :registered_at, :registered_at, :registered_at
                    )
                    ON CONFLICT (agent_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        version = EXCLUDED.version,
                        status = EXCLUDED.status,
                        capabilities = EXCLUDED.capabilities,
                        last_heartbeat = EXCLUDED.last_heartbeat,
                        updated_at = NOW()
                """),
                {
                    "agent_id": agent_info.agent_id,
                    "name": agent_info.name,
                    "description": agent_info.description or "",
                    "version": agent_info.version,
                    "status": agent_info.status,
                    "host": agent_info.host,
                    "port": agent_info.port,
                    "capabilities": agent_info.capabilities,
                    "required_permissions": agent_info.required_permissions,
                    "metadata": agent_info.metadata,
                    "reliability_score": agent_info.reliability_score,
                    "avg_latency_ms": agent_info.avg_latency_ms,
                    "cost_estimate": agent_info.cost_estimate,
                    "last_heartbeat": agent_info.last_heartbeat,
                    "registered_at": agent_info.registered_at,
                },
            )
            await session.commit()
    except Exception as e:
        logger.error("Failed to persist agent to DB", error=str(e))


# -------------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=int(settings.service_port))
