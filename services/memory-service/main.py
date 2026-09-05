"""
AgentOS — Memory Service

Implements 6 typed memory stores:
  working    → Redis (ephemeral, current task context)
  episodic   → PostgreSQL (past task executions)
  semantic   → PostgreSQL + pgvector (retrieved by similarity)
  procedural → PostgreSQL (agent operating procedures)
  evidence   → PostgreSQL + pgvector (source-backed facts)
  reflection → PostgreSQL (higher-order patterns)

Retrieval scoring formula:
  score = 0.45 × semantic_similarity
        + 0.20 × recency
        + 0.15 × importance
        + 0.10 × confidence
        + 0.10 × access_frequency
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter, Histogram
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from shared.config import settings
from shared.logging import configure_logging, get_logger
from shared.schemas.common import HealthResponse
from shared.schemas.memory import MemoryEntry, MemoryQuery, MemoryResult, MemoryType
from shared.tracing import configure_tracing, instrument_fastapi
from shared.utilities.llm.factory import get_embedding_provider

configure_logging(service_name="memory-service", log_level=settings.log_level)
configure_tracing(service_name="memory-service")
logger = get_logger(__name__)

engine = create_async_engine(settings.database_url, pool_size=10)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

memory_writes = Counter("agentos_memory_writes_total", "Memory writes", ["memory_type"])
memory_reads = Counter("agentos_memory_reads_total", "Memory reads", ["memory_type"])
embed_duration = Histogram("agentos_embedding_duration_seconds", "Embedding latency")

redis_client: Optional[aioredis.Redis] = None
embedder = None

WORKING_MEMORY_TTL = 3600  # 1 hour


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, embedder
    redis_client = await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    embedder = get_embedding_provider()
    logger.info("Memory Service started")
    yield
    if redis_client:
        await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="AgentOS — Memory Service",
    description="6-tier typed memory system with semantic retrieval.",
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
    checks = {}
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    try:
        async with SessionLocal() as s:
            await s.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    ok = all(v == "ok" for v in checks.values())
    return HealthResponse(
        status="healthy" if ok else "degraded",
        service="memory-service",
        checks=checks,
    )


@app.get("/readiness")
async def readiness():
    return {"status": "ready"}


# =========================================================================
# WRITE
# =========================================================================
@app.post("/memory", status_code=status.HTTP_201_CREATED, tags=["memory"])
async def store_memory(entry: MemoryEntry):
    memory_id = str(uuid4())
    memory_writes.labels(memory_type=entry.memory_type.value).inc()

    if entry.memory_type == MemoryType.WORKING:
        await _store_working(memory_id, entry)
    else:
        await _store_persistent(memory_id, entry)

    return {"memory_id": memory_id, "memory_type": entry.memory_type.value}


async def _store_working(memory_id: str, entry: MemoryEntry) -> None:
    """Store in Redis with TTL."""
    key = f"agentos:memory:working:{entry.tenant_id}:{entry.key or memory_id}"
    data = {
        "memory_id": memory_id,
        "content": entry.content,
        "agent_id": entry.agent_id or "",
        "metadata": json.dumps(entry.metadata),
        "confidence": str(entry.confidence),
        "importance": str(entry.importance),
    }
    await redis_client.hset(key, mapping=data)
    await redis_client.expire(key, WORKING_MEMORY_TTL)


async def _store_persistent(memory_id: str, entry: MemoryEntry) -> None:
    """Store in PostgreSQL, optionally generating an embedding."""
    embedding = None
    if entry.memory_type in (MemoryType.SEMANTIC, MemoryType.EVIDENCE):
        try:
            with embed_duration.time():
                embeddings = await embedder.embed([entry.content])
                embedding = embeddings[0] if embeddings else None
        except Exception as e:
            logger.warning("Embedding failed, storing without vector", error=str(e))

    async with SessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO memory (
                    id, tenant_id, agent_id, memory_type, key, content,
                    embedding, metadata, confidence, importance,
                    source_task_id, expires_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :agent_id, :memory_type, :key, :content,
                    :embedding, :metadata::jsonb, :confidence, :importance,
                    :source_task_id, :expires_at, NOW(), NOW()
                )
            """),
            {
                "id": memory_id,
                "tenant_id": entry.tenant_id,
                "agent_id": entry.agent_id,
                "memory_type": entry.memory_type.value,
                "key": entry.key,
                "content": entry.content,
                "embedding": str(embedding) if embedding else None,
                "metadata": json.dumps(entry.metadata),
                "confidence": entry.confidence,
                "importance": entry.importance,
                "source_task_id": entry.source_task_id,
                "expires_at": entry.expires_at,
            },
        )
        await session.commit()


# =========================================================================
# RETRIEVE
# =========================================================================
@app.post("/memory/search", tags=["memory"])
async def search_memory(query: MemoryQuery) -> list[MemoryResult]:
    """
    Retrieve memories using the composite scoring formula:
    score = 0.45 × semantic_similarity
          + 0.20 × recency
          + 0.15 × importance
          + 0.10 × confidence
          + 0.10 × access_frequency
    """
    memory_reads.labels(memory_type="search").inc()

    if query.memory_types and MemoryType.WORKING in query.memory_types:
        working_results = await _search_working(query)
    else:
        working_results = []

    persistent_types = [
        t for t in (query.memory_types or list(MemoryType))
        if t != MemoryType.WORKING
    ]

    if persistent_types:
        persistent_results = await _search_persistent(query, persistent_types)
    else:
        persistent_results = []

    all_results = working_results + persistent_results
    all_results.sort(key=lambda r: r.score, reverse=True)
    return all_results[:query.top_k]


async def _search_working(query: MemoryQuery) -> list[MemoryResult]:
    """Scan working memory keys for content match."""
    pattern = f"agentos:memory:working:{query.tenant_id}:*"
    results = []
    try:
        async for key in redis_client.scan_iter(pattern, count=100):
            data = await redis_client.hgetall(key)
            if not data:
                continue
            content = data.get("content", "")
            if query.query.lower() in content.lower():
                results.append(MemoryResult(
                    memory_id=data.get("memory_id", key),
                    memory_type=MemoryType.WORKING,
                    content=content,
                    score=0.5,
                    confidence=float(data.get("confidence", 0.5)),
                    importance=float(data.get("importance", 0.5)),
                    created_at=datetime.utcnow(),
                    metadata=json.loads(data.get("metadata", "{}")),
                ))
    except Exception as e:
        logger.warning("Working memory search failed", error=str(e))
    return results


async def _search_persistent(
    query: MemoryQuery,
    memory_types: list[MemoryType],
) -> list[MemoryResult]:
    """
    Semantic search in PostgreSQL using pgvector cosine similarity.
    Falls back to text ILIKE if embedding fails.
    """
    type_values = [t.value for t in memory_types]

    # Try embedding-based search first
    try:
        with embed_duration.time():
            query_embeddings = await embedder.embed([query.query])
        query_vec = query_embeddings[0]

        # Composite score via SQL
        sql = """
            WITH scored AS (
                SELECT
                    id::text as memory_id,
                    memory_type,
                    content,
                    confidence,
                    importance,
                    access_count,
                    created_at,
                    metadata,
                    -- Semantic similarity (cosine via pgvector)
                    CASE WHEN embedding IS NOT NULL
                        THEN 1 - (embedding <=> :query_vec::vector)
                        ELSE 0
                    END as semantic_sim,
                    -- Recency score (decay over 7 days)
                    GREATEST(0, 1 - EXTRACT(EPOCH FROM (NOW() - created_at)) / 604800) as recency,
                    -- Normalized access frequency
                    LEAST(1.0, access_count::float / 100) as access_freq
                FROM memory
                WHERE tenant_id = :tenant_id
                  AND memory_type = ANY(:memory_types)
                  AND (expires_at IS NULL OR expires_at > NOW())
                  AND archived = FALSE
            )
            SELECT *,
                0.45 * semantic_sim
                + 0.20 * recency
                + 0.15 * importance
                + 0.10 * confidence
                + 0.10 * access_freq AS composite_score
            FROM scored
            WHERE 0.45 * semantic_sim
                + 0.20 * recency
                + 0.15 * importance
                + 0.10 * confidence
                + 0.10 * access_freq >= :min_score
            ORDER BY composite_score DESC
            LIMIT :top_k
        """

        async with SessionLocal() as session:
            result = await session.execute(
                text(sql),
                {
                    "query_vec": f"[{','.join(str(x) for x in query_vec)}]",
                    "tenant_id": query.tenant_id,
                    "memory_types": type_values,
                    "min_score": query.min_score,
                    "top_k": query.top_k,
                },
            )
            rows = result.mappings().all()

        # Update access counts
        ids = [r["memory_id"] for r in rows]
        if ids:
            async with SessionLocal() as session:
                await session.execute(
                    text("UPDATE memory SET access_count = access_count + 1, last_accessed = NOW() WHERE id::text = ANY(:ids)"),
                    {"ids": ids},
                )
                await session.commit()

        return [
            MemoryResult(
                memory_id=r["memory_id"],
                memory_type=MemoryType(r["memory_type"]),
                content=r["content"],
                score=float(r["composite_score"] or 0),
                confidence=float(r["confidence"]),
                importance=float(r["importance"]),
                created_at=r["created_at"],
                metadata=r["metadata"] or {},
            )
            for r in rows
        ]

    except Exception as e:
        logger.warning("Semantic search failed, falling back to text search", error=str(e))
        return await _text_search_fallback(query, type_values)


async def _text_search_fallback(query: MemoryQuery, type_values: list) -> list[MemoryResult]:
    """Simple ILIKE text search when embedding unavailable."""
    async with SessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id::text as memory_id, memory_type, content, confidence, importance, created_at, metadata
                FROM memory
                WHERE tenant_id = :tenant_id
                  AND memory_type = ANY(:types)
                  AND content ILIKE :query
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY importance DESC, created_at DESC
                LIMIT :top_k
            """),
            {
                "tenant_id": query.tenant_id,
                "types": type_values,
                "query": f"%{query.query}%",
                "top_k": query.top_k,
            },
        )
        rows = result.mappings().all()

    return [
        MemoryResult(
            memory_id=r["memory_id"],
            memory_type=MemoryType(r["memory_type"]),
            content=r["content"],
            score=0.3,
            confidence=float(r["confidence"]),
            importance=float(r["importance"]),
            created_at=r["created_at"],
            metadata=r["metadata"] or {},
        )
        for r in rows
    ]


# =========================================================================
# ADMIN
# =========================================================================
@app.delete("/memory/{memory_id}", tags=["memory"])
async def delete_memory(memory_id: str, tenant_id: str = "default"):
    async with SessionLocal() as session:
        await session.execute(
            text("DELETE FROM memory WHERE id = :id AND tenant_id = :tenant_id"),
            {"id": memory_id, "tenant_id": tenant_id},
        )
        await session.commit()
    return {"deleted": memory_id}


@app.post("/memory/{memory_id}/archive", tags=["memory"])
async def archive_memory(memory_id: str):
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE memory SET archived = TRUE, updated_at = NOW() WHERE id = :id"),
            {"id": memory_id},
        )
        await session.commit()
    return {"archived": memory_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=int(settings.service_port))
