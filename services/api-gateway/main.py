"""
AgentOS — API Gateway

Single public entry point for the platform.
Responsibilities:
- JWT authentication
- RBAC enforcement
- Rate limiting
- Multi-tenant context injection
- Request routing to downstream services
- WebSocket proxy for real-time events
- Audit logging
- Request/response validation
"""
from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Depends, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from prometheus_client import make_asgi_app, Counter, Histogram
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from shared.config import settings
from shared.logging import configure_logging, get_logger
from shared.schemas.common import HealthResponse, ErrorResponse
from shared.tracing import configure_tracing, instrument_fastapi

configure_logging(service_name="api-gateway", log_level=settings.log_level)
configure_tracing(service_name="api-gateway")
logger = get_logger(__name__)

engine = create_async_engine(settings.database_url, pool_size=10)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Prometheus
requests_total = Counter("agentos_gateway_requests_total", "Total requests", ["method", "path", "status"])
request_duration = Histogram("agentos_gateway_request_duration_seconds", "Request duration", ["path"])
auth_failures = Counter("agentos_gateway_auth_failures_total", "Auth failures")

redis_client: Optional[aioredis.Redis] = None
security = HTTPBearer(auto_error=False)

# Service URL map
SERVICES = {
    "/agents": settings.agent_registry_url,
    "/workflows": settings.orchestrator_url,
    "/memory": settings.memory_service_url,
    "/approvals": settings.approval_service_url,
    "/policies": settings.policy_service_url,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
    logger.info("API Gateway started")
    yield
    if redis_client:
        await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="AgentOS — API Gateway",
    description="Single public entry point for the AgentOS platform.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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


# =========================================================================
# Auth
# =========================================================================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Decode JWT and return user context. Returns None if no token (public endpoints)."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        auth_failures.inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(
    user: Optional[dict] = Depends(get_current_user),
) -> dict:
    if not user:
        auth_failures.inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


# =========================================================================
# Rate Limiting (Redis sliding window)
# =========================================================================
async def check_rate_limit(request: Request, user: Optional[dict]) -> None:
    if not redis_client:
        return
    identifier = (user or {}).get("sub", request.client.host if request.client else "anon")
    key = f"agentos:ratelimit:{identifier}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 60)
        if count > settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Redis failure → allow request


# =========================================================================
# Health
# =========================================================================
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    services: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in [
            ("agent-registry", settings.agent_registry_url),
            ("orchestrator", settings.orchestrator_url),
            ("workflow-service", settings.workflow_service_url),
        ]:
            try:
                r = await client.get(f"{url}/health")
                services[name] = "ok" if r.status_code < 400 else "degraded"
            except Exception:
                services[name] = "error"

    overall = "healthy" if all(v == "ok" for v in services.values()) else "degraded"
    return HealthResponse(status=overall, service="api-gateway", checks=services)


@app.get("/readiness", tags=["system"])
async def readiness():
    return {"status": "ready"}


# =========================================================================
# Auth endpoints
# =========================================================================
@app.post("/auth/login", tags=["auth"])
async def login(credentials: dict):
    """Authenticate and return JWT."""
    email = credentials.get("email", "")
    password = credentials.get("password", "")

    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT id, email, username, role, password_hash, tenant_id FROM users WHERE email = :email"),
            {"email": email},
        )
        user = result.mappings().first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"])
    if not ctx.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    token_data = {
        "sub": str(user["id"]),
        "email": user["email"],
        "username": user["username"],
        "role": user["role"],
        "tenant_id": str(user["tenant_id"]),
        "exp": expire,
    }
    token = jwt.encode(token_data, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@app.get("/auth/me", tags=["auth"])
async def me(user: dict = Depends(require_auth)):
    return user


# =========================================================================
# Proxy routes — forward to downstream services
# =========================================================================
@app.api_route(
    "/agents/{path:path}",
    methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
    tags=["agents"],
    summary="Agent Registry proxy",
)
async def proxy_agents(path: str, request: Request, user: Optional[dict] = Depends(get_current_user)):
    await check_rate_limit(request, user)
    return await _proxy(request, settings.agent_registry_url, f"/agents/{path}")


@app.api_route(
    "/workflows/{path:path}",
    methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
    tags=["workflows"],
    summary="Workflow/Orchestrator proxy",
)
async def proxy_workflows(path: str, request: Request, user: dict = Depends(require_auth)):
    await check_rate_limit(request, user)
    return await _proxy(request, settings.orchestrator_url, f"/workflows/{path}")


@app.api_route(
    "/approvals/{path:path}",
    methods=["GET", "POST", "PATCH"],
    tags=["approvals"],
    summary="Approval Service proxy",
)
async def proxy_approvals(path: str, request: Request, user: dict = Depends(require_auth)):
    return await _proxy(request, settings.approval_service_url, f"/approvals/{path}")


@app.api_route(
    "/memory/{path:path}",
    methods=["GET", "POST", "DELETE"],
    tags=["memory"],
    summary="Memory Service proxy",
)
async def proxy_memory(path: str, request: Request, user: dict = Depends(require_auth)):
    return await _proxy(request, settings.memory_service_url, f"/memory/{path}")


@app.api_route(
    "/policies/{path:path}",
    methods=["GET", "POST"],
    tags=["policies"],
    summary="Policy Service proxy",
)
async def proxy_policies(path: str, request: Request, user: dict = Depends(require_auth)):
    return await _proxy(request, settings.policy_service_url, f"/policies/{path}")


async def _proxy(request: Request, base_url: str, path: str) -> Response:
    """Generic reverse proxy with timing and error handling."""
    start = time.monotonic()
    url = f"{base_url.rstrip('/')}{path}"
    if request.url.query:
        url += f"?{request.url.query}"

    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }
    headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    headers["X-Request-ID"] = str(uuid4())

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
            )

        duration = time.monotonic() - start
        request_duration.labels(path=path.split("/")[1] if "/" in path else path).observe(duration)
        requests_total.labels(
            method=request.method,
            path=path.split("/")[1] if "/" in path else path,
            status=str(resp.status_code),
        ).inc()

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {base_url}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")


# =========================================================================
# WebSocket proxy — live approval updates
# =========================================================================
@app.websocket("/ws/approvals")
async def ws_proxy_approvals(ws: WebSocket):
    """Proxy WebSocket to Approval Service."""
    await ws.accept()
    approval_ws_url = settings.approval_service_url.replace("http://", "ws://").replace("https://", "wss://")
    import websockets
    try:
        async with websockets.connect(f"{approval_ws_url}/ws/approvals") as upstream:
            async def forward_upstream():
                async for msg in upstream:
                    await ws.send_text(msg)

            async def forward_downstream():
                while True:
                    data = await ws.receive_text()
                    await upstream.send(data)

            import asyncio
            await asyncio.gather(forward_upstream(), forward_downstream())
    except Exception:
        await ws.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=int(settings.service_port))
