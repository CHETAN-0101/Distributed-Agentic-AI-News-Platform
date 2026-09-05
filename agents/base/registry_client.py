"""
AgentOS — Registry Client
Used by agents to self-register, send heartbeats, and deregister.
"""
from __future__ import annotations

from typing import Optional

import httpx

from shared.config import settings
from shared.logging import get_logger
from shared.schemas.agent import AgentRegistration, AgentHealthReport

logger = get_logger(__name__)


class RegistryClient:
    """HTTP client for the Agent Registry service."""

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = (base_url or settings.agent_registry_url).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=10.0,
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def register(self, registration: AgentRegistration) -> None:
        """Register this agent with the registry. Retries on failure."""
        if self._client is None:
            raise RuntimeError("RegistryClient not connected")

        for attempt in range(5):
            try:
                response = await self._client.post(
                    "/agents/register",
                    json=registration.model_dump(),
                )
                response.raise_for_status()
                logger.info(
                    "Agent registered",
                    agent_id=registration.agent_id,
                    attempt=attempt + 1,
                )
                return
            except Exception as e:
                import asyncio
                wait = 2 ** attempt
                logger.warning(
                    "Registration failed, retrying",
                    error=str(e),
                    attempt=attempt + 1,
                    wait_s=wait,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(f"Failed to register agent {registration.agent_id} after 5 attempts")

    async def heartbeat(self, report: AgentHealthReport) -> None:
        if self._client is None:
            return

        try:
            response = await self._client.post(
                f"/agents/{report.agent_id}/heartbeat",
                json=report.model_dump(),
            )
            response.raise_for_status()
        except Exception as e:
            logger.warning("Heartbeat request failed", error=str(e))

    async def deregister(self, agent_id: str) -> None:
        if self._client is None:
            return
        try:
            await self._client.delete(f"/agents/{agent_id}")
        except Exception as e:
            logger.warning("Deregister failed", error=str(e))
