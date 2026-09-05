"""
AgentOS — Agent Router

Finds the best available agent for a required capability.
Scoring considers: reliability, latency, cost, queue depth, circuit state.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from shared.config import settings
from shared.logging import get_logger
from shared.schemas.agent import AgentInfo, CircuitBreakerState

logger = get_logger(__name__)


class AgentRouter:
    """Selects the best agent for a given capability."""

    def __init__(self, registry_url: Optional[str] = None):
        self._registry_url = (registry_url or settings.agent_registry_url).rstrip("/")

    async def find_best_agent(
        self,
        capability: str,
        min_reliability: float = 0.0,
        task_priority: str = "NORMAL",
    ) -> Optional[AgentInfo]:
        """
        Find and score agents for a capability.

        Scoring formula:
            score = 0.5 × reliability
                  + 0.3 × (1 - normalized_latency)
                  + 0.2 × (1 - normalized_cost)

        For CRITICAL priority: weight reliability at 0.7.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self._registry_url}/agents/discover/{capability}",
                    params={"min_reliability": min_reliability},
                )
                resp.raise_for_status()
                agents_data = resp.json()
            except Exception as e:
                logger.error(
                    "Agent discovery failed",
                    capability=capability,
                    error=str(e),
                )
                return None

        if not agents_data:
            logger.warning("No agents found for capability", capability=capability)
            return None

        agents = [AgentInfo(**a) for a in agents_data]

        if task_priority == "CRITICAL":
            # For critical tasks, prefer reliability over speed
            def score(a: AgentInfo) -> float:
                lat = (a.avg_latency_ms or 1000) / 10000
                return 0.7 * a.reliability_score - 0.3 * lat
        else:
            def score(a: AgentInfo) -> float:
                lat = (a.avg_latency_ms or 1000) / 10000
                cost = (a.cost_estimate or 0.05) * 10
                return 0.5 * a.reliability_score - 0.3 * lat - 0.2 * min(cost, 1.0)

        best = max(agents, key=score)
        logger.debug(
            "Agent selected",
            capability=capability,
            agent_id=best.agent_id,
            reliability=best.reliability_score,
        )
        return best

    async def get_all_capabilities(self) -> dict[str, str]:
        """Return a dict of {capability: agent_name} for all healthy agents."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self._registry_url}/agents",
                    params={"status": "healthy", "page_size": 200},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("Failed to fetch agents", error=str(e))
                return {}

        capabilities: dict[str, str] = {}
        for agent_data in data.get("items", []):
            agent_name = agent_data.get("name", "")
            for cap in agent_data.get("capabilities", []):
                capabilities[cap] = agent_name

        return capabilities
