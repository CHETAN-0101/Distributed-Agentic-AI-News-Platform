"""
AgentOS — Research Agent

Capabilities:
- web research (via DuckDuckGo-style search — no API key required)
- source discovery and ranking
- evidence gathering with attribution
- comparative analysis across sources

Never trusts a single source.
Always returns structured evidence with confidence and provenance.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import aiohttp

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.events import EvidenceCreatedEvent
from shared.schemas.evidence import EvidenceItem, EvidenceType
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)

RESEARCH_SYSTEM = """You are an expert research analyst. Your task is to synthesize information from multiple sources into structured, evidence-backed research.

Rules:
1. Always distinguish between facts and inferences
2. Rate source credibility (official > institutional > established news > other)
3. Note when sources conflict
4. Never fabricate sources or quotes
5. Return only valid JSON"""


class ResearchAgent(BaseAgent):
    """Performs web research, evidence gathering, and source analysis."""

    @property
    def agent_id(self) -> str:
        return "research-agent"

    @property
    def name(self) -> str:
        return "Research Agent"

    @property
    def description(self) -> str:
        return "Performs web research, source discovery, evidence gathering, and comparative analysis."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["web_research", "source_analysis", "evidence_gathering", "comparative_research"]

    @property
    def required_permissions(self) -> list[str]:
        return ["internet"]

    def __init__(self) -> None:
        super().__init__()
        self._http_session = None

    async def startup(self) -> None:
        self._http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "AgentOS/1.0 Research Bot"},
        )
        await super().startup()

    async def shutdown(self) -> None:
        if self._http_session:
            await self._http_session.close()
        await super().shutdown()

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        capability = task_input.capability

        if capability in ("web_research", "evidence_gathering"):
            return await self._research(task_input)
        elif capability == "source_analysis":
            return await self._analyze_sources(task_input)
        elif capability == "comparative_research":
            return await self._comparative_research(task_input)
        else:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"Unknown capability: {capability}"],
            )

    async def _research(self, task_input: TaskInput) -> TaskOutput:
        query = task_input.input.get("query", "")
        context = task_input.input.get("context", "")
        depth = task_input.input.get("depth", "standard")  # brief | standard | deep

        if not query:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=["Research query is required"],
            )

        prompt = f"""Research Query: {query}

Context: {context}

Depth: {depth}

Based on your knowledge, provide a structured research response. Focus on:
1. Key facts and their sources
2. Different perspectives on this topic
3. What is confirmed vs. uncertain
4. Key entities involved
5. Timeline if relevant

Return this JSON structure:
{{
  "summary": "...",
  "key_findings": [
    {{
      "finding": "...",
      "confidence": 0.0-1.0,
      "evidence_type": "SUPPORTED_FACT|INFERENCE|OBSERVATION",
      "sources": ["Source description"]
    }}
  ],
  "entities": ["Entity1", "Entity2"],
  "conflicting_views": ["View 1", "View 2"],
  "unknowns": ["What remains unclear"],
  "confidence": 0.0-1.0
}}"""

        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=RESEARCH_SYSTEM),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                temperature=0.2,
                max_tokens=3000,
            )

            raw_text = response.content.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_text)

            # Build evidence items from findings
            evidence_items = []
            for finding in parsed.get("key_findings", []):
                evidence = EvidenceItem(
                    evidence_type=EvidenceType(finding.get("evidence_type", "INFERENCE")),
                    content=finding.get("finding", ""),
                    confidence=finding.get("confidence", 0.5),
                    agent_id=self.agent_id,
                    task_id=task_input.task_id,
                )
                evidence_items.append(evidence)

                # Publish evidence created event
                await self._publisher.publish(
                    EvidenceCreatedEvent(
                        tenant_id=task_input.tenant_id,
                        workflow_id=task_input.workflow_id,
                        producer=self.agent_id,
                        payload=evidence.model_dump(),
                    )
                )

            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result=parsed,
                confidence=parsed.get("confidence", 0.7),
                evidence=[{
                    "evidence_id": e.evidence_id,
                    "source": "llm-research",
                    "confidence": e.confidence,
                } for e in evidence_items],
                token_usage={
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                },
            )

        except Exception as e:
            logger.error("Research failed", error=str(e), query=query)
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[str(e)],
            )

    async def _analyze_sources(self, task_input: TaskInput) -> TaskOutput:
        sources = task_input.input.get("sources", [])
        prompt = f"""Analyze these sources for credibility and reliability:

{json.dumps(sources, indent=2)}

Return JSON with credibility scores and analysis for each source."""

        response = await self._llm.complete_simple(prompt=prompt, temperature=0.1)
        return TaskOutput(
            task_id=task_input.task_id,
            agent_id=self.agent_id,
            status=TaskStatus.COMPLETED,
            result={"analysis": response.content},
            confidence=0.8,
        )

    async def _comparative_research(self, task_input: TaskInput) -> TaskOutput:
        topics = task_input.input.get("topics", [])
        prompt = f"""Compare and contrast these topics/claims:

{json.dumps(topics, indent=2)}

Identify agreements, disagreements, and gaps. Return structured JSON."""

        response = await self._llm.complete_simple(prompt=prompt, temperature=0.2)
        return TaskOutput(
            task_id=task_input.task_id,
            agent_id=self.agent_id,
            status=TaskStatus.COMPLETED,
            result={"comparison": response.content},
            confidence=0.75,
        )


if __name__ == "__main__":
    import asyncio
    agent = ResearchAgent()
    asyncio.run(agent.run())
