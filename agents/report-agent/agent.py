"""
AgentOS — Report Agent

Synthesizes multi-agent workflow results into structured, human-readable reports.
Supports:
- Executive summary reports
- Technical analysis reports
- News intelligence briefings
- Cross-domain investigation reports
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)

REPORT_SYSTEM = """You are an expert report writer and analyst.

Your task is to synthesize findings from multiple AI agents into clear, structured, professional reports.

Rules:
1. Clearly separate confirmed facts from inferences
2. Always cite which agent or source produced each finding
3. Include confidence levels for key conclusions
4. Structure reports with clear sections
5. Include actionable recommendations where appropriate
6. Never present uncertain information as definitive
7. Return valid JSON"""


class ReportAgent(BaseAgent):
    """Synthesizes workflow results into structured reports."""

    @property
    def agent_id(self) -> str:
        return "report-agent"

    @property
    def name(self) -> str:
        return "Report Agent"

    @property
    def description(self) -> str:
        return "Synthesizes multi-agent results into structured, evidence-backed reports."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["report_synthesis", "executive_summary", "technical_report", "news_briefing"]

    @property
    def required_permissions(self) -> list[str]:
        return ["llm"]

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        capability = task_input.capability

        if capability in ("report_synthesis", "executive_summary", "technical_report", "news_briefing"):
            return await self._generate_report(task_input, capability)
        else:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"Unknown capability: {capability}"],
            )

    async def _generate_report(self, task_input: TaskInput, report_type: str) -> TaskOutput:
        workflow_results = task_input.input.get("workflow_results", {})
        context = task_input.input.get("context", {})
        goal = task_input.input.get("goal", "Generate a comprehensive report")

        results_summary = json.dumps(workflow_results, indent=2, default=str)
        if len(results_summary) > 6000:
            results_summary = results_summary[:6000] + "\n... [truncated for length]"

        report_guidance = {
            "report_synthesis": "Comprehensive synthesis of all findings with clear sections",
            "executive_summary": "Brief executive summary: key findings, confidence, recommendations (1 page)",
            "technical_report": "Detailed technical report with methodology, evidence, and analysis",
            "news_briefing": "News-style briefing: what happened, confirmed, disputed, unknown, why it matters",
        }

        prompt = f"""Goal: {goal}

Report Type: {report_type}
Format: {report_guidance.get(report_type, 'Comprehensive')}

Workflow Results from Multiple Agents:
{results_summary}

Context: {json.dumps(context, default=str)}

Generate a structured report. Return this JSON:
{{
  "title": "...",
  "report_type": "{report_type}",
  "executive_summary": "...",
  "key_findings": [
    {{
      "finding": "...",
      "confidence": 0.0-1.0,
      "source_agents": ["agent_id"],
      "evidence_count": 0
    }}
  ],
  "confirmed_facts": ["..."],
  "uncertain_points": ["..."],
  "recommendations": ["..."],
  "confidence": 0.0-1.0,
  "generated_at": "{datetime.utcnow().isoformat()}"
}}"""

        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=REPORT_SYSTEM),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                temperature=0.2,
                max_tokens=4000,
            )

            raw_text = response.content.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_text)

            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result=parsed,
                confidence=float(parsed.get("confidence", 0.8)),
                token_usage={
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                },
            )

        except json.JSONDecodeError as e:
            # Fallback: return raw text as unstructured report
            logger.warning("Report JSON parse failed, returning raw", error=str(e))
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result={"report": response.content, "format": "unstructured"},
                confidence=0.6,
                warnings=["Report could not be parsed as structured JSON"],
            )
        except Exception as e:
            logger.error("Report generation failed", error=str(e))
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[str(e)],
            )


if __name__ == "__main__":
    import asyncio
    agent = ReportAgent()
    asyncio.run(agent.run())
