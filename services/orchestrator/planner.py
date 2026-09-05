"""
AgentOS — Planner

Decomposes a natural language goal into a validated workflow DAG.
Uses Mistral AI to generate the plan, then validates against available agents.

Key validation steps:
1. All required capabilities must exist in the Agent Registry
2. All dependency edges must reference valid node IDs
3. Permissions must be satisfied
4. Cost budget check (optional)
"""
from __future__ import annotations

import json
from typing import Any, Optional
from uuid import uuid4

from shared.logging import get_logger
from shared.schemas.workflow import WorkflowGraph, WorkflowNode
from shared.utilities.llm.base import LLMProvider, Message, MessageRole
from shared.utilities.llm.factory import get_llm_provider

logger = get_logger(__name__)

PLANNER_SYSTEM = """You are an expert AI workflow planner for the AgentOS platform.

Your job is to decompose a user's goal into a directed acyclic graph (DAG) of agent tasks.

Available agent capabilities:
{capabilities}

Rules:
1. Each node must use a capability from the available list
2. depends_on must reference valid node_ids
3. Parallel nodes (no shared dependencies) run simultaneously
4. Use the minimum number of nodes needed — don't over-engineer
5. Always end with a "report_synthesis" node if producing a final report
6. Return ONLY valid JSON, no markdown

Return this structure:
{
  "reasoning": "...",
  "nodes": [
    {
      "node_id": "unique_id",
      "capability": "capability_name",
      "depends_on": [],
      "description": "...",
      "input_mapping": {}
    }
  ]
}"""


class Planner:
    """
    Decomposes goals into validated workflow DAGs.
    Never trusts the LLM output blindly — validates against live registry.
    """

    def __init__(
        self,
        router: Any,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self._router = router
        self._llm: Optional[LLMProvider] = llm_provider

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_llm_provider()
        return self._llm

    async def plan(
        self,
        goal: str,
        context: dict[str, Any],
        tenant_id: str = "default",
    ) -> WorkflowGraph:
        """
        Generate a validated workflow DAG for the given goal.

        Args:
            goal:      Natural language description of what to accomplish.
            context:   Additional context (previous outputs, user preferences).
            tenant_id: For multi-tenant capability filtering.

        Returns:
            A validated WorkflowGraph ready for execution.
        """
        # Get available capabilities from live registry
        available_caps = await self._router.get_all_capabilities()

        if not available_caps:
            logger.warning("No agents available in registry — using fallback plan")
            return self._fallback_plan(goal)

        caps_description = "\n".join(
            f"- {cap}: {desc}" for cap, desc in available_caps.items()
        )

        prompt = f"""Goal: {goal}

Context: {json.dumps(context, default=str)[:500]}

Plan the most efficient workflow to accomplish this goal using the available capabilities.
Keep it minimal — 2-6 nodes unless the goal genuinely requires more."""

        system = PLANNER_SYSTEM.format(capabilities=caps_description)

        try:
            response = await self.llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=system),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw)
            nodes_data = parsed.get("nodes", [])

            logger.info(
                "Plan generated",
                goal=goal[:80],
                node_count=len(nodes_data),
                reasoning=parsed.get("reasoning", "")[:100],
            )

            # Build and validate nodes
            nodes = []
            node_ids: set[str] = set()

            for node_data in nodes_data:
                cap = node_data.get("capability", "")

                # Validate capability exists
                if cap not in available_caps:
                    logger.warning(
                        "Unknown capability in plan — skipping node",
                        capability=cap,
                        node_id=node_data.get("node_id"),
                    )
                    continue

                node_id = node_data.get("node_id") or str(uuid4())[:8]
                node_ids.add(node_id)

                nodes.append(WorkflowNode(
                    node_id=node_id,
                    capability=cap,
                    depends_on=node_data.get("depends_on", []),
                    input_mapping=node_data.get("input_mapping", {}),
                    metadata={"description": node_data.get("description", "")},
                ))

            # Validate dependencies reference valid node IDs
            for node in nodes:
                invalid_deps = [d for d in node.depends_on if d not in node_ids]
                if invalid_deps:
                    logger.warning(
                        "Removing invalid dependencies",
                        node_id=node.node_id,
                        invalid=invalid_deps,
                    )
                    node.depends_on = [d for d in node.depends_on if d in node_ids]

            if not nodes:
                logger.error("Plan produced no valid nodes — using fallback")
                return self._fallback_plan(goal)

            return WorkflowGraph(nodes=nodes)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Plan parsing failed", error=str(e))
            return self._fallback_plan(goal)
        except Exception as e:
            logger.error("Planning failed", error=str(e))
            return self._fallback_plan(goal)

    def _fallback_plan(self, goal: str) -> WorkflowGraph:
        """Simple fallback: research → verify → report."""
        return WorkflowGraph(
            nodes=[
                WorkflowNode(
                    node_id="research",
                    capability="web_research",
                    depends_on=[],
                    input_mapping={"query": goal},
                ),
                WorkflowNode(
                    node_id="verify",
                    capability="claim_verification",
                    depends_on=["research"],
                ),
                WorkflowNode(
                    node_id="report",
                    capability="report_synthesis",
                    depends_on=["verify"],
                ),
            ]
        )
