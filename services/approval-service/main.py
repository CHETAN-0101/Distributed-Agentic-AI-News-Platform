"""
AgentOS — Approval Service

Manages human-in-the-loop approval gates.
Integrates with Workflow Service to pause/resume workflows.

States: pending → approved | rejected | expired | cancelled

Approval requests expire automatically (configurable TTL).
WebSocket endpoint pushes real-time updates to the frontend.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Gauge, Counter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from shared.config import settings
from shared.logging import configure_logging, get_logger
from shared.messaging.publisher import EventPublisher
from shared.schemas.approval import ApprovalRequest, ApprovalDecision, RiskLevel
from shared.schemas.common import HealthResponse
from shared.schemas.events import HumanApprovedEvent, HumanRejectedEvent
from shared.tracing import configure_tracing, instrument_fastapi

configure_logging(service_name="approval-service", log_level=settings.log_level)
configure_tracing(service_name="approval-service")
logger = get_logger(__name__)

engine = create_async_engine(settings.database_url, pool_size=5)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

pending_approvals = Gauge("agentos_pending_approvals", "Pending approval requests")
approvals_total = Counter("agentos_approvals_total", "Total approvals", ["decision"])

publisher: Optional[EventPublisher] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self.active.remove(ws)

ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global publisher
    publisher = EventPublisher()
    await publisher.connect()
    # Start expiry monitor
    expiry_task = asyncio.create_task(_expiry_monitor())
    logger.info("Approval Service started")
    yield
    expiry_task.cancel()
    await publisher.close()
    await engine.dispose()


app = FastAPI(
    title="AgentOS — Approval Service",
    description="Human-in-the-loop approval gate management.",
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
    return HealthResponse(
        status="healthy",
        service="approval-service",
        checks={"pending": int(pending_approvals._value.get())},
    )


@app.get("/readiness")
async def readiness():
    return {"status": "ready"}


# =========================================================================
# APPROVAL REQUESTS
# =========================================================================
@app.post("/approvals", status_code=status.HTTP_201_CREATED, tags=["approvals"])
async def create_approval(request: ApprovalRequest):
    """Submit a new approval request (called by orchestrator/agents)."""
    import json as _json

    async with SessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO approval_requests (
                    id, tenant_id, workflow_id, task_id, requested_by,
                    action, risk_level, reason, evidence, proposed_change,
                    rollback_plan, status, expires_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :workflow_id, :task_id, :requested_by,
                    :action, :risk_level, :reason, :evidence::jsonb, :proposed_change::jsonb,
                    :rollback_plan::jsonb, 'pending', :expires_at, NOW(), NOW()
                )
            """),
            {
                "id": request.approval_id,
                "tenant_id": request.tenant_id,
                "workflow_id": request.workflow_id,
                "task_id": request.task_id,
                "requested_by": request.requested_by,
                "action": request.action,
                "risk_level": request.risk_level.value,
                "reason": request.reason,
                "evidence": _json.dumps(request.evidence),
                "proposed_change": _json.dumps(request.proposed_change),
                "rollback_plan": _json.dumps(request.rollback_plan),
                "expires_at": request.expires_at,
            },
        )
        await session.commit()

    pending_approvals.inc()
    await ws_manager.broadcast({
        "event": "approval_required",
        "approval_id": request.approval_id,
        "action": request.action,
        "risk_level": request.risk_level.value,
        "reason": request.reason,
        "expires_at": request.expires_at.isoformat(),
    })

    logger.info(
        "Approval request created",
        approval_id=request.approval_id,
        action=request.action,
        risk=request.risk_level,
    )
    return {"approval_id": request.approval_id, "status": "pending"}


@app.get("/approvals", tags=["approvals"])
async def list_approvals(
    tenant_id: str = "default",
    approval_status: str = "pending",
):
    async with SessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, workflow_id, task_id, requested_by, action, risk_level,
                       reason, status, expires_at, created_at
                FROM approval_requests
                WHERE tenant_id = :tenant_id AND status = :status
                ORDER BY risk_level DESC, created_at ASC
            """),
            {"tenant_id": tenant_id, "status": approval_status},
        )
        rows = result.mappings().all()
    return {"approvals": [dict(r) for r in rows]}


@app.get("/approvals/{approval_id}", tags=["approvals"])
async def get_approval(approval_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM approval_requests WHERE id = :id"),
            {"id": approval_id},
        )
        row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    return dict(row)


@app.post("/approvals/{approval_id}/decide", tags=["approvals"])
async def decide_approval(approval_id: str, decision: ApprovalDecision):
    """Approve or reject an action. Publishes event to resume/cancel workflow."""
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM approval_requests WHERE id = :id"),
            {"id": approval_id},
        )
        row = result.mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    if row["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval already in state: {row['status']}",
        )

    async with SessionLocal() as session:
        await session.execute(
            text("""
                UPDATE approval_requests
                SET status = :status, reviewer_id = :reviewer_id,
                    reviewer_note = :note, reviewed_at = NOW(), updated_at = NOW()
                WHERE id = :id
            """),
            {
                "id": approval_id,
                "status": decision.decision,
                "reviewer_id": decision.reviewer_id,
                "note": decision.reviewer_note,
            },
        )
        await session.commit()

    pending_approvals.dec()
    approvals_total.labels(decision=decision.decision).inc()

    # Publish event so orchestrator can resume or cancel the workflow
    if decision.decision == "approved":
        event = HumanApprovedEvent(
            tenant_id=row["tenant_id"],
            workflow_id=row["workflow_id"],
            producer="approval-service",
            payload={"approval_id": approval_id, "reviewer": decision.reviewer_id},
        )
    else:
        event = HumanRejectedEvent(
            tenant_id=row["tenant_id"],
            workflow_id=row["workflow_id"],
            producer="approval-service",
            payload={
                "approval_id": approval_id,
                "reviewer": decision.reviewer_id,
                "reason": decision.reviewer_note,
            },
        )

    await publisher.publish(event)
    await ws_manager.broadcast({
        "event": f"approval_{decision.decision}",
        "approval_id": approval_id,
        "decision": decision.decision,
    })

    logger.info(
        "Approval decided",
        approval_id=approval_id,
        decision=decision.decision,
        reviewer=decision.reviewer_id,
    )
    return {
        "approval_id": approval_id,
        "decision": decision.decision,
        "workflow_id": row["workflow_id"],
    }


# =========================================================================
# WEBSOCKET — live updates to frontend
# =========================================================================
@app.websocket("/ws/approvals")
async def websocket_approvals(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# =========================================================================
# Background: expire old approvals
# =========================================================================
async def _expiry_monitor():
    while True:
        await asyncio.sleep(60)
        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    text("""
                        UPDATE approval_requests
                        SET status = 'expired', updated_at = NOW()
                        WHERE status = 'pending' AND expires_at < NOW()
                        RETURNING id, workflow_id
                    """)
                )
                expired = result.fetchall()
                await session.commit()

            for row in expired:
                pending_approvals.dec()
                logger.warning("Approval expired", approval_id=str(row[0]))
                await ws_manager.broadcast({
                    "event": "approval_expired",
                    "approval_id": str(row[0]),
                    "workflow_id": str(row[1]),
                })
        except Exception as e:
            logger.error("Expiry monitor error", error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=int(settings.service_port))
