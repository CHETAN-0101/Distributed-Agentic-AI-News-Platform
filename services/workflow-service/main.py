"""
AgentOS — Workflow Service

Persists workflow state, DAG nodes, and tasks.
Source of truth for: what is running, what completed, what failed.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Gauge
from sqlalchemy import text, select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from shared.config import settings
from shared.logging import configure_logging, get_logger
from shared.schemas.common import HealthResponse, PaginatedResponse
from shared.tracing import configure_tracing, instrument_fastapi

configure_logging(service_name="workflow-service", log_level=settings.log_level)
configure_tracing(service_name="workflow-service")
logger = get_logger(__name__)

engine = create_async_engine(settings.database_url, pool_size=10)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

active_wf_gauge = Gauge("agentos_workflow_service_active", "Active workflows in DB")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Workflow Service starting")
    yield
    await engine.dispose()


app = FastAPI(
    title="AgentOS — Workflow Service",
    description="Persistent workflow state management and DAG tracking.",
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


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    try:
        async with SessionLocal() as s:
            await s.execute(text("SELECT 1"))
        return HealthResponse(status="healthy", service="workflow-service")
    except Exception:
        return HealthResponse(status="unhealthy", service="workflow-service")


@app.get("/readiness", tags=["system"])
async def readiness():
    return {"status": "ready"}


# -------------------------------------------------------------------------
# Workflows
# -------------------------------------------------------------------------
@app.post("/workflows", status_code=status.HTTP_201_CREATED, tags=["workflows"])
async def create_workflow(data: dict):
    workflow_id = data.get("id") or str(uuid4())
    async with SessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO workflows (id, tenant_id, name, description, status, priority,
                    graph, input, trace_id, idempotency_key, deadline, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :description, :status, :priority,
                    :graph::jsonb, :input::jsonb, :trace_id, :idempotency_key, :deadline, NOW(), NOW())
                ON CONFLICT (idempotency_key) DO NOTHING
            """),
            {
                "id": workflow_id,
                "tenant_id": data.get("tenant_id", "default"),
                "name": data.get("name", "Unnamed"),
                "description": data.get("description", ""),
                "status": "pending",
                "priority": data.get("priority", "NORMAL"),
                "graph": __import__("json").dumps(data.get("graph", {})),
                "input": __import__("json").dumps(data.get("input", {})),
                "trace_id": data.get("trace_id"),
                "idempotency_key": data.get("idempotency_key"),
                "deadline": data.get("deadline"),
            },
        )
        await session.commit()
    return {"id": workflow_id, "status": "pending"}


@app.get("/workflows", tags=["workflows"])
async def list_workflows(
    tenant_id: str = Query("default"),
    wf_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * page_size
    query = """
        SELECT id, name, status, priority, trace_id, started_at, completed_at, created_at, updated_at
        FROM workflows
        WHERE tenant_id = :tenant_id
    """
    params: dict = {"tenant_id": tenant_id, "limit": page_size, "offset": offset}
    if wf_status:
        query += " AND status = :status"
        params["status"] = wf_status
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    async with SessionLocal() as session:
        result = await session.execute(text(query), params)
        rows = result.mappings().all()
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM workflows WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        total = count_result.scalar()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/workflows/{workflow_id}", tags=["workflows"])
async def get_workflow(workflow_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM workflows WHERE id = :id"), {"id": workflow_id}
        )
        row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return dict(row)


@app.patch("/workflows/{workflow_id}", tags=["workflows"])
async def update_workflow(workflow_id: str, data: dict):
    allowed_fields = {"status", "output", "error", "graph", "started_at", "completed_at"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    if not updates:
        return {"message": "No valid fields to update"}

    set_parts = []
    params: dict = {"id": workflow_id}
    for k, v in updates.items():
        if k in ("output", "error", "graph"):
            set_parts.append(f"{k} = :{k}::jsonb")
            params[k] = __import__("json").dumps(v) if v is not None else None
        else:
            set_parts.append(f"{k} = :{k}")
            params[k] = v

    set_clause = ", ".join(set_parts)
    async with SessionLocal() as session:
        await session.execute(
            text(f"UPDATE workflows SET {set_clause}, updated_at = NOW() WHERE id = :id"),
            params,
        )
        await session.commit()
    return {"workflow_id": workflow_id, "updated": list(updates.keys())}


@app.post("/workflows/{workflow_id}/cancel", tags=["workflows"])
async def cancel_workflow(workflow_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT status FROM workflows WHERE id = :id"), {"id": workflow_id}
        )
        row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await update_workflow(workflow_id, {"status": "cancelled"})
    return {"workflow_id": workflow_id, "status": "cancelled"}


# -------------------------------------------------------------------------
# Tasks
# -------------------------------------------------------------------------
@app.post("/tasks", status_code=status.HTTP_201_CREATED, tags=["tasks"])
async def create_task(data: dict):
    task_id = data.get("task_id") or str(uuid4())
    async with SessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO tasks (id, tenant_id, workflow_id, agent_id, capability,
                    status, priority, input, idempotency_key, created_at, updated_at)
                VALUES (:id, :tenant_id, :workflow_id, :agent_id, :capability,
                    'pending', :priority, :input::jsonb, :idempotency_key, NOW(), NOW())
                ON CONFLICT (idempotency_key) DO NOTHING
            """),
            {
                "id": task_id,
                "tenant_id": data.get("tenant_id", "default"),
                "workflow_id": data.get("workflow_id"),
                "agent_id": data.get("agent_id"),
                "capability": data.get("capability", ""),
                "priority": data.get("priority", "NORMAL"),
                "input": __import__("json").dumps(data.get("input", {})),
                "idempotency_key": data.get("idempotency_key"),
            },
        )
        await session.commit()
    return {"id": task_id, "status": "pending"}


@app.get("/tasks/{task_id}", tags=["tasks"])
async def get_task(task_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id}
        )
        row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)


@app.patch("/tasks/{task_id}", tags=["tasks"])
async def update_task(task_id: str, data: dict):
    allowed = {"status", "output", "error", "confidence", "execution_ms", "completed_at", "started_at"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return {"message": "Nothing to update"}

    set_parts = []
    params: dict = {"id": task_id}
    for k, v in updates.items():
        if k == "output":
            set_parts.append(f"{k} = :{k}::jsonb")
            params[k] = __import__("json").dumps(v) if v else None
        else:
            set_parts.append(f"{k} = :{k}")
            params[k] = v

    async with SessionLocal() as session:
        await session.execute(
            text(f"UPDATE tasks SET {', '.join(set_parts)}, updated_at = NOW() WHERE id = :id"),
            params,
        )
        await session.commit()
    return {"task_id": task_id, "updated": list(updates.keys())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=int(settings.service_port))
