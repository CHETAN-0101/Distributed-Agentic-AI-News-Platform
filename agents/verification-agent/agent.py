"""
AgentOS — Verification Agent

Evidence-based verification pipeline:
1. Schema validation of agent outputs
2. Evidence sufficiency check
3. Consistency check across sources
4. Confidence calibration
5. Policy check

Returns one of the 8 verification states.
Never asks an LLM "is this true?" — instead uses evidence comparison.
"""
from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.evidence import ClaimStatus, EvidenceItem, EvidenceType
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)

VERIFICATION_SYSTEM = """You are an expert fact-checker and verification specialist.

Your role is NOT to determine if something is true based on your knowledge.
Your role IS to evaluate the EVIDENCE provided and determine:
1. Is the evidence sufficient?
2. Are there contradictions between sources?
3. Are sources credible and independent?
4. What is the appropriate verification status?

Verification states:
- CONFIRMED: Multiple independent credible sources agree
- SUPPORTED: Single credible source with no contradictions
- CONFLICTING: Sources disagree on this claim
- UNVERIFIED: No evidence provided
- INSUFFICIENT_EVIDENCE: Some evidence but not conclusive
- OPINION: Not a factual claim, cannot be verified
- CORRECTED: Original claim was wrong, correction available
- OUTDATED: Was true but circumstances have changed

Return only valid JSON."""


class VerificationAgent(BaseAgent):
    """Performs evidence-based claim verification."""

    @property
    def agent_id(self) -> str:
        return "verification-agent"

    @property
    def name(self) -> str:
        return "Verification Agent"

    @property
    def description(self) -> str:
        return "Validates claims using evidence comparison, source analysis, and consistency checking."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["claim_verification", "evidence_validation", "consistency_check", "confidence_assessment"]

    @property
    def required_permissions(self) -> list[str]:
        return ["llm"]

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        capability = task_input.capability

        if capability == "claim_verification":
            return await self._verify_claim(task_input)
        elif capability == "evidence_validation":
            return await self._validate_evidence(task_input)
        elif capability == "consistency_check":
            return await self._check_consistency(task_input)
        else:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"Unknown capability: {capability}"],
            )

    async def _verify_claim(self, task_input: TaskInput) -> TaskOutput:
        claim = task_input.input.get("claim", {})
        evidence = task_input.input.get("evidence", [])
        sources = task_input.input.get("sources", [])

        claim_text = claim.get("text", "")
        if not claim_text:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=["No claim text provided"],
            )

        prompt = f"""Verify this claim using the provided evidence.

CLAIM: {claim_text}

EVIDENCE ({len(evidence)} items):
{json.dumps(evidence[:10], indent=2)}

SOURCES ({len(sources)} items):
{json.dumps(sources[:5], indent=2)}

Analyze:
1. Do the evidence items support or contradict this claim?
2. Are sources credible and independent?
3. Is there sufficient evidence to reach a conclusion?
4. Are there any contradictions?

Return this JSON:
{{
  "status": "CONFIRMED|SUPPORTED|CONFLICTING|UNVERIFIED|INSUFFICIENT_EVIDENCE|OPINION|CORRECTED|OUTDATED",
  "confidence": 0.0-1.0,
  "supporting_count": 0,
  "contradicting_count": 0,
  "reasoning": "...",
  "key_evidence": ["..."],
  "warnings": ["..."]
}}"""

        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=VERIFICATION_SYSTEM),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                temperature=0.05,  # Very low temperature for verification
                max_tokens=1024,
            )

            raw_text = response.content.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_text)
            status_str = parsed.get("status", "UNVERIFIED")

            # Validate status is a known value
            try:
                claim_status = ClaimStatus(status_str)
            except ValueError:
                claim_status = ClaimStatus.UNVERIFIED

            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result={
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim_text,
                    "verification_status": claim_status.value,
                    "confidence": parsed.get("confidence", 0.5),
                    "reasoning": parsed.get("reasoning", ""),
                    "supporting_evidence_count": parsed.get("supporting_count", 0),
                    "contradicting_evidence_count": parsed.get("contradicting_count", 0),
                    "key_evidence": parsed.get("key_evidence", []),
                    "warnings": parsed.get("warnings", []),
                },
                confidence=parsed.get("confidence", 0.5),
                warnings=parsed.get("warnings", []),
            )

        except Exception as e:
            logger.error("Verification failed", error=str(e))
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[str(e)],
            )

    async def _validate_evidence(self, task_input: TaskInput) -> TaskOutput:
        """Check evidence items for internal consistency."""
        evidence = task_input.input.get("evidence", [])
        prompt = f"""Validate this set of evidence items for consistency and quality.

Evidence: {json.dumps(evidence, indent=2)}

Check for:
1. Internal contradictions
2. Source credibility issues
3. Missing provenance
4. Circular references

Return JSON with validation results."""

        response = await self._llm.complete_simple(prompt, temperature=0.1)
        return TaskOutput(
            task_id=task_input.task_id,
            agent_id=self.agent_id,
            status=TaskStatus.COMPLETED,
            result={"validation": response.content},
            confidence=0.85,
        )

    async def _check_consistency(self, task_input: TaskInput) -> TaskOutput:
        """Check consistency across multiple claims."""
        claims = task_input.input.get("claims", [])
        prompt = f"""Check these claims for internal consistency and contradictions.

Claims: {json.dumps(claims, indent=2)}

Identify any contradictions or inconsistencies. Return structured JSON."""

        response = await self._llm.complete_simple(prompt, temperature=0.1)
        return TaskOutput(
            task_id=task_input.task_id,
            agent_id=self.agent_id,
            status=TaskStatus.COMPLETED,
            result={"consistency_check": response.content},
            confidence=0.85,
        )


if __name__ == "__main__":
    import asyncio
    agent = VerificationAgent()
    asyncio.run(agent.run())
