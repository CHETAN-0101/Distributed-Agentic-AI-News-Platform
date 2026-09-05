"""
AgentOS — Orchestrator Service

Responsibilities:
1. Accept workflow creation requests
2. Use the Planner to decompose goals into agent DAGs
3. Submit workflows to the Workflow Engine
4. Monitor execution progress
5. Route tasks to the best available agent via Agent Registry
6. Handle failures, retries, fallbacks
7. Enforce policies before execution
8. Request human approval when required
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from shared.config import settings
from shared.logging import configure_logging, get_logger
from shared.messaging.publisher import EventPublisher
from shared.schemas.common import HealthResponse, ErrorResponse
from shared.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowStatus, WorkflowGraph, WorkflowNode
from shared.schemas.events import WorkflowStartedEvent
from shared.tracing import configure_tracing, instrument_fastapi
from .planner import Planner
from .router import AgentRouter

configure_logging(service_name="orchestrator", log_level=settings.log_level)
configure_tracing(service_name="orchestrator")

logger = get_logger(__name__)

# -------------------------------------------------------------------------
# Infrastructure
# -------------------------------------------------------------------------
engine = create_async_engine(settings.database_url, pool_size=10)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Prometheus metrics
workflows_started = Counter("agentos_workflows_started_total", "Workflows started")
workflows_completed = Counter("agentos_workflows_completed_total", "Workflows completed", ["status"])
active_workflows = Gauge("agentos_active_workflows", "Currently active workflows")
planning_duration = Histogram("agentos_planning_duration_seconds", "Time to plan a workflow")


# -------------------------------------------------------------------------
# App Lifecycle
# -------------------------------------------------------------------------
publisher: Optional[EventPublisher] = None
planner: Optional[Planner] = None
router: Optional[AgentRouter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global publisher, planner, router
    publisher = EventPublisher()
    await publisher.connect()

    router = AgentRouter(registry_url=settings.agent_registry_url)
    planner = Planner(router=router, llm_provider=None)  # LLM injected lazily

    logger.info("Orchestrator started")
    yield
    await publisher.close()
    await engine.dispose()
    logger.info("Orchestrator stopped")


app = FastAPI(
    title="AgentOS — Orchestrator",
    description="Plans, routes, and orchestrates multi-agent workflows.",
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


# -------------------------------------------------------------------------
# Health
# -------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse(
        status="healthy",
        service="orchestrator",
        checks={"active_workflows": int(active_workflows._value.get())},
    )


@app.get("/readiness", tags=["system"])
async def readiness():
    return {"status": "ready"}


# -------------------------------------------------------------------------
# Workflow API
# -------------------------------------------------------------------------
@app.post(
    "/workflows",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["workflows"],
    summary="Create and start a new workflow",
)
async def create_workflow(
    request: WorkflowCreate,
    background_tasks: BackgroundTasks,
):
    """
    Accept a workflow request. If `graph` is provided, execute it directly.
    If only `goal` is provided, the Planner decomposes it into a graph first.
    """
    workflow_id = str(uuid4())
    trace_id = str(uuid4())

    # Forward to Workflow Service for persistence
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.workflow_service_url}/workflows",
                json={**request.model_dump(), "id": workflow_id, "trace_id": trace_id},
            )
            resp.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Workflow Service unavailable: {e}",
            )

    # Fire-and-forget execution
    background_tasks.add_task(
        _execute_workflow,
        workflow_id=workflow_id,
        request=request,
        trace_id=trace_id,
    )

    workflows_started.inc()
    active_workflows.inc()

    logger.info("Workflow accepted", workflow_id=workflow_id, name=request.name)

    return {
        "workflow_id": workflow_id,
        "status": "accepted",
        "trace_id": trace_id,
        "message": "Workflow queued for execution",
    }


@app.post(
    "/workflows/{workflow_id}/cancel",
    tags=["workflows"],
    summary="Cancel a running workflow",
)
async def cancel_workflow(workflow_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.workflow_service_url}/workflows/{workflow_id}/cancel"
        )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Workflow not found")
    return {"workflow_id": workflow_id, "status": "cancel_requested"}


@app.get(
    "/workflows/{workflow_id}",
    tags=["workflows"],
    summary="Get workflow status",
)
async def get_workflow(workflow_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.workflow_service_url}/workflows/{workflow_id}"
        )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return resp.json()


# -------------------------------------------------------------------------
# Background execution
# -------------------------------------------------------------------------
async def _execute_workflow(
    workflow_id: str,
    request: WorkflowCreate,
    trace_id: str,
) -> None:
    """
    Async background task:
    1. Plan (if goal-only)
    2. Publish workflow.started event
    3. Dispatch tasks to agents via RabbitMQ
    """
    try:
        # Step 1: Plan if no explicit graph
        if request.graph is None and request.goal:
            with planning_duration.time():
                graph = await planner.plan(
                    goal=request.goal,
                    context=request.input,
                    tenant_id=request.tenant_id,
                )
        elif request.graph:
            graph = request.graph
        else:
            graph = WorkflowGraph(nodes=[])

        # Step 2: Update workflow with graph
        await _update_workflow_graph(workflow_id, graph)

        # Step 3: Publish workflow started event
        await publisher.publish(
            WorkflowStartedEvent(
                tenant_id=request.tenant_id,
                workflow_id=workflow_id,
                trace_id=trace_id,
                producer="orchestrator",
                payload={"name": request.name, "node_count": len(graph.nodes)},
            )
        )

        # Step 4: Execute graph nodes
        await _execute_graph(workflow_id, graph, request, trace_id)

    except Exception as e:
        logger.error("Workflow execution failed", workflow_id=workflow_id, error=str(e))
        await _mark_workflow_failed(workflow_id, str(e))
        workflows_completed.labels(status="failed").inc()
    finally:
        active_workflows.dec()


async def _execute_graph(
    workflow_id: str,
    graph: WorkflowGraph,
    request: WorkflowCreate,
    trace_id: str,
) -> None:
    """Execute the workflow DAG respecting dependencies."""
    from shared.schemas.task import TaskInput, TaskPriority

    completed: dict[str, Any] = {}
    failed: set[str] = set()
    pending = {node.node_id: node for node in graph.nodes}

    while pending:
        # Find nodes whose dependencies are all satisfied
        ready = [
            node for node in pending.values()
            if all(dep in completed for dep in node.depends_on)
            and not any(dep in failed for dep in node.depends_on)
        ]

        if not ready:
            if pending:
                logger.error(
                    "Workflow deadlock — no nodes ready",
                    workflow_id=workflow_id,
                    pending_nodes=list(pending.keys()),
                    failed_nodes=list(failed),
                )
            break

        # Execute ready nodes in parallel
        tasks = []
        for node in ready:
            del pending[node.node_id]
            tasks.append(_execute_node(workflow_id, node, request, trace_id, completed))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for node, result in zip(ready, results):
            if isinstance(result, Exception):
                logger.error("Node execution failed", node_id=node.node_id, error=str(result))
                failed.add(node.node_id)
            else:
                completed[node.node_id] = result

    # Mark workflow complete
    if failed:
        await _mark_workflow_failed(workflow_id, f"Nodes failed: {list(failed)}")
        workflows_completed.labels(status="failed").inc()
    else:
        await _mark_workflow_completed(workflow_id, completed)
        workflows_completed.labels(status="completed").inc()


async def _execute_node(
    workflow_id: str,
    node: WorkflowNode,
    request: WorkflowCreate,
    trace_id: str,
    completed_outputs: dict,
) -> dict:
    """Execute a single workflow node by dispatching to an agent."""
    from shared.schemas.task import TaskInput, TaskPriority
    from shared.schemas.events import TaskCreatedEvent

    # Resolve input from previous node outputs
    node_input = {**request.input}
    for dep in node.depends_on:
        if dep in completed_outputs:
            node_input[f"_from_{dep}"] = completed_outputs[dep]
    node_input.update(node.input_mapping)

    # Find the best agent for this capability
    agent = await router.find_best_agent(node.capability)
    if not agent:
        raise RuntimeError(f"No available agent for capability: {node.capability}")

    task = TaskInput(
        workflow_id=workflow_id,
        agent_id=agent.agent_id,
        capability=node.capability,
        input=node_input,
        priority=request.priority,
        tenant_id=request.tenant_id,
        trace_id=trace_id,
        correlation_id=str(uuid4()),
        max_retries=node.max_retries,
    )

    # Publish task to agent's queue
    await publisher.publish(
        TaskCreatedEvent(
            tenant_id=request.tenant_id,
            workflow_id=workflow_id,
            task_id=task.task_id,
            producer="orchestrator",
            trace_id=trace_id,
            payload=task.model_dump(),
        )
    )

    logger.info(
        "Task dispatched",
        workflow_id=workflow_id,
        node_id=node.node_id,
        capability=node.capability,
        agent_id=agent.agent_id,
        task_id=task.task_id,
    )

    # Wait for task completion (simplified — production uses event listener)
    return await _wait_for_task(task.task_id, timeout=120)


async def _wait_for_task(task_id: str, timeout: int = 120) -> dict:
    """Poll for task completion (production version uses Redis pub/sub or DB events)."""
    import time
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(timeout=5.0) as client:
        while time.monotonic() < deadline:
            try:
                resp = await client.get(f"{settings.workflow_service_url}/tasks/{task_id}")
                if resp.status_code == 200:
                    task_data = resp.json()
                    if task_data.get("status") in ("completed", "failed", "dead"):
                        return task_data
            except Exception:
                pass
            await asyncio.sleep(2)
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


async def _update_workflow_graph(workflow_id: str, graph: WorkflowGraph) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.patch(
                f"{settings.workflow_service_url}/workflows/{workflow_id}",
                json={"graph": graph.model_dump(), "status": "running"},
            )
        except Exception as e:
            logger.warning("Could not update workflow graph", error=str(e))


async def _mark_workflow_completed(workflow_id: str, outputs: dict) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.patch(
                f"{settings.workflow_service_url}/workflows/{workflow_id}",
                json={"status": "completed", "output": outputs},
            )
        except Exception as e:
            logger.warning("Could not mark workflow complete", error=str(e))


async def _mark_workflow_failed(workflow_id: str, reason: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.patch(
                f"{settings.workflow_service_url}/workflows/{workflow_id}",
                json={"status": "failed", "error": {"reason": reason}},
            )
        except Exception as e:
            logger.warning("Could not mark workflow failed", error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=int(settings.service_port))
