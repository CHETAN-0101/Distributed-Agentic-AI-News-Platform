"""
AgentOS — News Summary Agent

Produces three levels of evidence-backed summaries:
- brief_30s: Maximum brevity
- brief_60s: Main facts + implications
- deep: Full evidence-backed explanation

Each summary explicitly separates:
- What happened (confirmed)
- What is disputed
- What remains unknown
- Why it matters
- Sources with evidence
- Timeline
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.evidence import ClaimStatus
from shared.schemas.news import NewsSummary, TimelineEntry
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)


SUMMARY_SYSTEM = """You are an expert news analyst and fact-checker. Your role is to produce balanced, evidence-based news summaries that clearly distinguish between:
- CONFIRMED facts (multiple independent sources agree)
- SUPPORTED claims (single credible source)
- CONFLICTING information (sources disagree)
- UNKNOWN information (not yet established)
- OPINION (not a factual claim)

You NEVER present uncertainty as certainty.
You NEVER make up sources.
You ALWAYS cite the basis for your categorization.
You return only valid JSON."""


def _build_summary_prompt(event_data: dict, summary_type: str, claims: list[dict]) -> str:
    title = event_data.get("title", "Unknown Event")
    articles = event_data.get("articles", [])
    timeline = event_data.get("timeline", [])

    confirmed = [c for c in claims if c.get("status") == "CONFIRMED"]
    supported = [c for c in claims if c.get("status") == "SUPPORTED"]
    conflicting = [c for c in claims if c.get("status") == "CONFLICTING"]
    unverified = [c for c in claims if c.get("status") in ("UNVERIFIED", "INSUFFICIENT_EVIDENCE")]

    length_guidance = {
        "brief_30s": "1-2 sentences maximum. Only the single most important fact.",
        "brief_60s": "3-5 sentences. Core facts, key implication.",
        "deep": "Comprehensive. Full context, all evidence, implications, and unknowns.",
    }

    return f"""Event: {title}

Summary Type: {summary_type}
Length Guidance: {length_guidance.get(summary_type, 'Moderate length')}

Sources: {len(articles)} articles

CONFIRMED CLAIMS ({len(confirmed)}):
{json.dumps([c.get('text') for c in confirmed[:10]], indent=2)}

SUPPORTED CLAIMS ({len(supported)}):
{json.dumps([c.get('text') for c in supported[:5]], indent=2)}

CONFLICTING CLAIMS ({len(conflicting)}):
{json.dumps([c.get('text') for c in conflicting[:5]], indent=2)}

UNVERIFIED ({len(unverified)}):
{json.dumps([c.get('text') for c in unverified[:5]], indent=2)}

TIMELINE ENTRIES:
{json.dumps(timeline[:10], indent=2)}

Produce a summary following this EXACT JSON structure:
{{
  "what_happened": "...",
  "confirmed": ["list of confirmed facts"],
  "conflicting": ["list of conflicting/disputed points"],
  "unknown": ["list of what remains unclear"],
  "why_it_matters": "...",
  "confidence": 0.0-1.0,
  "key_entities": ["Entity1", "Entity2"],
  "source_count": {len(articles)}
}}"""


class NewsSummaryAgent(BaseAgent):
    """Generates evidence-backed news summaries distinguishing confirmed from disputed."""

    @property
    def agent_id(self) -> str:
        return "news-summary-agent"

    @property
    def name(self) -> str:
        return "News Summary Agent"

    @property
    def description(self) -> str:
        return "Produces evidence-backed news summaries with explicit confirmed/disputed/unknown separation."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["news_summarize", "news_brief_30s", "news_brief_60s", "news_deep_brief"]

    @property
    def required_permissions(self) -> list[str]:
        return ["llm"]

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        capability = task_input.capability

        if capability in ("news_summarize", "news_brief_30s", "news_brief_60s", "news_deep_brief"):
            summary_type_map = {
                "news_summarize": "brief_60s",
                "news_brief_30s": "brief_30s",
                "news_brief_60s": "brief_60s",
                "news_deep_brief": "deep",
            }
            return await self._generate_summary(task_input, summary_type_map[capability])
        else:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"Unknown capability: {capability}"],
            )

    async def _generate_summary(self, task_input: TaskInput, summary_type: str) -> TaskOutput:
        event_data = task_input.input.get("event", {})
        claims = task_input.input.get("claims", [])
        event_id = event_data.get("event_id", task_input.input.get("event_id", ""))

        if not event_data:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=["No event data provided"],
            )

        prompt = _build_summary_prompt(event_data, summary_type, claims)

        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=SUMMARY_SYSTEM),
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

            # Build typed summary
            summary = NewsSummary(
                event_id=event_id,
                summary_type=summary_type,
                what_happened=parsed.get("what_happened", ""),
                confirmed=parsed.get("confirmed", []),
                conflicting=parsed.get("conflicting", []),
                unknown=parsed.get("unknown", []),
                why_it_matters=parsed.get("why_it_matters", ""),
                confidence=float(parsed.get("confidence", 0.7)),
                sources=[{"source": a.get("source", ""), "url": a.get("url", "")}
                         for a in event_data.get("articles", [])[:10]],
            )

            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result=summary.model_dump(),
                confidence=summary.confidence,
                token_usage={
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                },
            )

        except json.JSONDecodeError as e:
            logger.error("Summary JSON parse failed", error=str(e))
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"LLM returned invalid JSON: {e}"],
            )
        except Exception as e:
            logger.error("Summary generation failed", error=str(e))
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[str(e)],
            )


if __name__ == "__main__":
    import asyncio
    agent = NewsSummaryAgent()
    asyncio.run(agent.run())
