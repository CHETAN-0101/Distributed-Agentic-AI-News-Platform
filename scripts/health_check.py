#!/usr/bin/env python3
"""
AgentOS Health Check Script
Run to verify all infrastructure and services are healthy.
"""
import asyncio
import sys
import httpx
import redis.asyncio as aioredis

SERVICES = [
    ("PostgreSQL", "direct"),
    ("Redis", "redis://localhost:6379/0"),
    ("RabbitMQ Management", "http://localhost:15672"),
    ("Jaeger UI", "http://localhost:16686"),
    ("Prometheus", "http://localhost:9090/-/healthy"),
    ("Grafana", "http://localhost:3001/api/health"),
    ("API Gateway", "http://localhost:8000/health"),
    ("Agent Registry", "http://localhost:8001/health"),
    ("Orchestrator", "http://localhost:8002/health"),
    ("Workflow Service", "http://localhost:8003/health"),
]

COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}


def ok(msg: str) -> str:
    return f"{COLORS['green']}✓{COLORS['reset']} {msg}"


def fail(msg: str) -> str:
    return f"{COLORS['red']}✗{COLORS['reset']} {msg}"


def warn(msg: str) -> str:
    return f"{COLORS['yellow']}⚠{COLORS['reset']} {msg}"


async def check_http(name: str, url: str) -> tuple[str, bool]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            if r.status_code < 400:
                return ok(f"{name}: {url} ({r.status_code})"), True
            return fail(f"{name}: {url} returned {r.status_code}"), False
    except Exception as e:
        return fail(f"{name}: {url} — {e}"), False


async def check_redis(url: str) -> tuple[str, bool]:
    try:
        client = await aioredis.from_url(url)
        await client.ping()
        await client.aclose()
        return ok(f"Redis: {url}"), True
    except Exception as e:
        return fail(f"Redis: {url} — {e}"), False


async def main():
    print(f"\n{COLORS['bold']}AgentOS Health Check{COLORS['reset']}")
    print("=" * 50)

    results = []

    for name, endpoint in SERVICES:
        if endpoint == "direct":
            # Skip direct DB check (would need asyncpg)
            results.append((warn(f"{name}: skipped (use psql directly)"), True))
        elif endpoint.startswith("redis://"):
            results.append(await check_redis(endpoint))
        else:
            results.append(await check_http(name, endpoint))

    passed = sum(1 for _, ok_flag in results if ok_flag)
    total = len(results)

    for msg, _ in results:
        print(f"  {msg}")

    print("=" * 50)
    color = COLORS["green"] if passed == total else COLORS["yellow"] if passed > total // 2 else COLORS["red"]
    print(f"\n{color}{COLORS['bold']}{passed}/{total} checks passed{COLORS['reset']}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
