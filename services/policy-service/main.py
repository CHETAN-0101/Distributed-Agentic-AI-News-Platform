"""
AgentOS — Policy Service

Evaluates actions against configured policies.
Determines risk level and whether human approval is required.

Policy evaluation order (highest priority first):
1. Exact action match
2. Pattern match (regex)
3. Default allow with LOW risk
"""
from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from shared.config import settings
from shared.logging import configure_logging, get_logger
from shared.schemas.common import HealthResponse
from shared.tracing import configure_tracing, instrument_fastapi

configure_logging(service_name="policy-service", log_level=settings.log_level)
configure_tracing(service_name="policy-service")
logger = get_logger(__name__)

engine = create_async_engine(settings.database_url, pool_size=5)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
policy_evaluations = Counter("agentos_policy_evaluations_total", "Policy evaluations", ["result"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="AgentOS — Policy Service",
    description="RBAC, risk evaluation, and action policy enforcement.",
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
app.mount("/metrics", make_asgi_app())


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", service="policy-service")


@app.get("/readiness")
async def readiness():
    return {"status": "ready"}


@app.post("/evaluate", tags=["policy"])
async def evaluate_action(request: dict):
    """
    Evaluate whether an action is permitted.

    Input:
        action:     The action identifier (e.g. "delete_database", "security.scan.run")
        agent_id:   The agent requesting the action
        user_role:  Role of the requesting user
        tenant_id:  Tenant context
        context:    Additional context for rule evaluation

    Output:
        allowed:            bool
        risk_level:         LOW | MEDIUM | HIGH | CRITICAL
        requires_approval:  bool
        matched_policy:     policy name or None
        reason:             explanation
    """
    action = request.get("action", "")
    user_role = request.get("user_role", "user")
    tenant_id = request.get("tenant_id", "default")

    # Load active policies ordered by priority
    async with SessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT name, action_pattern, risk_level, requires_approval, allowed_roles, priority
                FROM policies
                WHERE tenant_id = :tenant_id AND is_active = TRUE
                ORDER BY priority DESC
            """),
            {"tenant_id": tenant_id},
        )
        policies = result.mappings().all()

    # Evaluate policies in priority order
    for policy in policies:
        pattern = policy["action_pattern"]
        try:
            if re.match(pattern, action, re.IGNORECASE):
                # Check role
                allowed_roles = policy["allowed_roles"] or []
                role_allowed = not allowed_roles or user_role in allowed_roles

                if not role_allowed:
                    policy_evaluations.labels(result="denied").inc()
                    return {
                        "allowed": False,
                        "risk_level": policy["risk_level"],
                        "requires_approval": False,
                        "matched_policy": policy["name"],
                        "reason": f"Role '{user_role}' not in allowed roles: {allowed_roles}",
                    }

                policy_evaluations.labels(result="evaluated").inc()
                return {
                    "allowed": True,
                    "risk_level": policy["risk_level"],
                    "requires_approval": policy["requires_approval"],
                    "matched_policy": policy["name"],
                    "reason": f"Matched policy: {policy['name']}",
                }
        except re.error:
            # Invalid regex — skip
            continue

    # Default: allow with LOW risk
    policy_evaluations.labels(result="default_allow").inc()
    return {
        "allowed": True,
        "risk_level": "LOW",
        "requires_approval": False,
        "matched_policy": None,
        "reason": "No matching policy — default allow",
    }


@app.get("/policies", tags=["policy"])
async def list_policies(tenant_id: str = "default"):
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM policies WHERE tenant_id = :tenant_id ORDER BY priority DESC"),
            {"tenant_id": tenant_id},
        )
        rows = result.mappings().all()
    return {"policies": [dict(r) for r in rows]}


@app.post("/policies", status_code=status.HTTP_201_CREATED, tags=["policy"])
async def create_policy(data: dict):
    import json
    async with SessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO policies (tenant_id, name, action_pattern, risk_level,
                    requires_approval, allowed_roles, priority, created_at, updated_at)
                VALUES (:tenant_id, :name, :action_pattern, :risk_level,
                    :requires_approval, :allowed_roles, :priority, NOW(), NOW())
                ON CONFLICT (tenant_id, name) DO UPDATE SET
                    action_pattern = EXCLUDED.action_pattern,
                    risk_level = EXCLUDED.risk_level,
                    requires_approval = EXCLUDED.requires_approval,
                    updated_at = NOW()
            """),
            {
                "tenant_id": data.get("tenant_id", "default"),
                "name": data["name"],
                "action_pattern": data["action_pattern"],
                "risk_level": data.get("risk_level", "LOW"),
                "requires_approval": data.get("requires_approval", False),
                "allowed_roles": data.get("allowed_roles", []),
                "priority": data.get("priority", 0),
            },
        )
        await session.commit()
    return {"status": "created", "name": data["name"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=int(settings.service_port))
