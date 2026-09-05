"""
AgentOS — Security Agent

Capabilities:
- log_analysis: Analyze logs for security incidents
- vulnerability_analysis: Assess CVEs and vulnerabilities
- incident_analysis: Investigate security incidents
- security_posture: Evaluate overall security posture

IMPORTANT: No offensive actions without explicit policy authorization.
All high-risk actions require human approval via Policy Service.
"""
from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)

SECURITY_SYSTEM = """You are an expert cybersecurity analyst.

Your role is to analyze security data and provide actionable, evidence-based assessments.

Rules:
1. Only perform DEFENSIVE analysis — no offensive actions
2. Always rate severity: CRITICAL | HIGH | MEDIUM | LOW | INFO
3. Provide specific, actionable remediation steps
4. Cite CVEs, standards (OWASP, NIST, CIS) where relevant
5. Never fabricate vulnerability data
6. Return valid JSON only"""


class SecurityAgent(BaseAgent):

    @property
    def agent_id(self) -> str:
        return "security-agent"

    @property
    def name(self) -> str:
        return "Security Agent"

    @property
    def description(self) -> str:
        return "Analyzes security logs, vulnerabilities, and incidents. Defensive only."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["log_analysis", "vulnerability_analysis", "incident_analysis", "security_posture"]

    @property
    def required_permissions(self) -> list[str]:
        return ["security_logs.read", "llm"]

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        cap = task_input.capability
        handlers = {
            "log_analysis": self._analyze_logs,
            "vulnerability_analysis": self._analyze_vulnerability,
            "incident_analysis": self._analyze_incident,
            "security_posture": self._assess_posture,
        }
        handler = handlers.get(cap)
        if not handler:
            return TaskOutput(task_id=task_input.task_id, agent_id=self.agent_id,
                              status=TaskStatus.FAILED, errors=[f"Unknown: {cap}"])
        return await handler(task_input)

    async def _analyze_logs(self, task: TaskInput) -> TaskOutput:
        logs = task.input.get("logs", "")
        timeframe = task.input.get("timeframe", "last 1 hour")
        prompt = f"""Analyze these security logs for threats, anomalies, and incidents.

Timeframe: {timeframe}
Logs: {str(logs)[:3000]}

Return JSON:
{{
  "threats": [{{"type": "...", "severity": "CRITICAL|HIGH|MEDIUM|LOW", "description": "...", "indicator": "..."}}],
  "anomalies": ["..."],
  "summary": "...",
  "recommended_actions": ["..."],
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _analyze_vulnerability(self, task: TaskInput) -> TaskOutput:
        vuln_data = task.input.get("vulnerability", {})
        cve = vuln_data.get("cve_id", "")
        description = vuln_data.get("description", "")
        prompt = f"""Analyze this vulnerability for risk and remediation.

CVE: {cve}
Description: {description}

Return JSON:
{{
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "cvss_estimate": 0.0-10.0,
  "affected_components": ["..."],
  "attack_vector": "...",
  "remediation": ["Step 1", "Step 2"],
  "workarounds": ["..."],
  "references": ["CVE link", "Vendor advisory"],
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _analyze_incident(self, task: TaskInput) -> TaskOutput:
        incident = task.input.get("incident", {})
        prompt = f"""Investigate this security incident.

Incident: {json.dumps(incident, default=str)[:2000]}

Return JSON:
{{
  "incident_type": "...",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "timeline": [{{"time": "...", "event": "..."}}],
  "root_cause": "...",
  "scope": "...",
  "containment_steps": ["..."],
  "eradication_steps": ["..."],
  "lessons_learned": ["..."],
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _assess_posture(self, task: TaskInput) -> TaskOutput:
        config = task.input.get("configuration", {})
        prompt = f"""Assess the security posture based on this configuration.

Configuration: {json.dumps(config, default=str)[:2000]}

Return JSON:
{{
  "overall_score": 0-100,
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "strengths": ["..."],
  "gaps": [{{"gap": "...", "severity": "...", "recommendation": "..."}}],
  "compliance_notes": {{"OWASP": "...", "NIST": "..."}},
  "confidence": 0.0-1.0
}}"""
        return await self._llm_task(task, prompt)

    async def _llm_task(self, task: TaskInput, prompt: str) -> TaskOutput:
        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=SECURITY_SYSTEM),
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
            result = json.loads(raw)
            return TaskOutput(
                task_id=task.task_id, agent_id=self.agent_id,
                status=TaskStatus.COMPLETED, result=result,
                confidence=float(result.get("confidence", 0.7)),
                token_usage={"prompt_tokens": response.prompt_tokens,
                             "completion_tokens": response.completion_tokens,
                             "total_tokens": response.total_tokens},
            )
        except Exception as e:
            return TaskOutput(task_id=task.task_id, agent_id=self.agent_id,
                              status=TaskStatus.FAILED, errors=[str(e)])


if __name__ == "__main__":
    import asyncio
    asyncio.run(SecurityAgent().run())
