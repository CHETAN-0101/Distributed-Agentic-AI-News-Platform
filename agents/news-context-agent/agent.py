"""
AgentOS — News Context Agent

Adds background, historical context, and implications to a news event.
"Why does this matter?" + "What led to this?" + "What happens next?"

Capabilities:
- news_context: Background + implications
- historical_context: Timeline of related past events
- impact_analysis: Economic, social, political implications
- stakeholder_analysis: Who is affected and how
"""
from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)

CONTEXT_SYSTEM = """You are an expert political analyst, economist, and historian.

Your role is to provide accurate, nuanced background and context for news events.

Rules:
1. Clearly label what is established historical fact vs. current analysis
2. Present multiple stakeholder perspectives without bias
3. Quantify impact with concrete figures where possible
4. Identify what is uncertain about future developments
5. Return valid JSON"""


class NewsContextAgent(BaseAgent):

    @property
    def agent_id(self) -> str:
        return "news-context-agent"

    @property
    def name(self) -> str:
        return "News Context Agent"

    @property
    def description(self) -> str:
        return "Provides background, historical context, and implications for news events."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["news_context", "historical_context", "impact_analysis", "stakeholder_analysis"]

    @property
    def required_permissions(self) -> list[str]:
        return ["llm"]

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        cap = task_input.capability
        handlers = {
            "news_context": self._build_context,
            "historical_context": self._historical,
            "impact_analysis": self._impact,
            "stakeholder_analysis": self._stakeholders,
        }
        handler = handlers.get(cap)
        if not handler:
            return TaskOutput(task_id=task_input.task_id, agent_id=self.agent_id,
                              status=TaskStatus.FAILED, errors=[f"Unknown: {cap}"])
        return await handler(task_input)

    async def _build_context(self, task: TaskInput) -> TaskOutput:
        event = task.input.get("event", {})
        title = event.get("title", "")
        summary = task.input.get("summary", "")

        prompt = f"""Provide background context for this news event.

Event Title: {title}
Summary: {summary}

Return JSON:
{{
  "background": "2-3 paragraphs of relevant background",
  "key_historical_context": ["Past event 1", "Past event 2"],
  "why_it_matters": "Explanation of significance",
  "short_term_implications": ["..."],
  "long_term_implications": ["..."],
  "related_events": [{{"title": "...", "date": "...", "relevance": "..."}}],
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _historical(self, task: TaskInput) -> TaskOutput:
        topic = task.input.get("topic", "")
        years_back = task.input.get("years_back", 10)
        prompt = f"""Provide historical context for: {topic}

Look back {years_back} years. Include key events, turning points, and patterns.

Return JSON:
{{
  "timeline": [{{"year": 2020, "event": "...", "significance": "..."}}],
  "key_patterns": ["..."],
  "relevant_precedents": ["..."],
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _impact(self, task: TaskInput) -> TaskOutput:
        event = task.input.get("event", {})
        domains = task.input.get("domains", ["economic", "social", "political"])
        prompt = f"""Analyze the multi-domain impact of this event.

Event: {json.dumps(event, default=str)[:1500]}
Domains to analyze: {domains}

Return JSON:
{{
  "economic_impact": {{"short_term": "...", "long_term": "...", "magnitude": "high|medium|low"}},
  "social_impact": {{"affected_groups": ["..."], "description": "..."}},
  "political_impact": {{"domestic": "...", "international": "..."}},
  "overall_significance": "high|medium|low",
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _stakeholders(self, task: TaskInput) -> TaskOutput:
        event = task.input.get("event", {})
        prompt = f"""Identify all key stakeholders for this event and analyze their interests.

Event: {json.dumps(event, default=str)[:1500]}

Return JSON:
{{
  "stakeholders": [
    {{
      "name": "...",
      "type": "government|corporation|ngo|individual|public",
      "position": "...",
      "interests": ["..."],
      "likely_response": "..."
    }}
  ],
  "conflict_points": ["..."],
  "cooperation_opportunities": ["..."],
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _llm_task(self, task: TaskInput, prompt: str) -> TaskOutput:
        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=CONTEXT_SYSTEM),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                temperature=0.2, max_tokens=2500,
            )
            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            result = json.loads(raw)
            return TaskOutput(
                task_id=task.task_id, agent_id=self.agent_id,
                status=TaskStatus.COMPLETED, result=result,
                confidence=float(result.get("confidence", 0.75)),
                token_usage={"prompt_tokens": response.prompt_tokens,
                             "completion_tokens": response.completion_tokens,
                             "total_tokens": response.total_tokens},
            )
        except Exception as e:
            return TaskOutput(task_id=task.task_id, agent_id=self.agent_id,
                              status=TaskStatus.FAILED, errors=[str(e)])


if __name__ == "__main__":
    import asyncio
    asyncio.run(NewsContextAgent().run())
