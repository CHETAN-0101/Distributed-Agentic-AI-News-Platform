"""
AgentOS — News Claim Extraction Agent

Uses Mistral AI to extract structured factual claims from news articles.
Each claim is stored with:
- Subject-Predicate-Object triple
- Source article reference
- Confidence score
- Evidence metadata

Publishes news.claim.extracted events.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.events import NewsClaimExtractedEvent
from shared.schemas.evidence import Claim, ClaimStatus
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)

CLAIM_EXTRACTION_SYSTEM = """You are an expert journalist and fact-checker specializing in extracting verifiable factual claims from news articles.

Your task is to identify SPECIFIC, VERIFIABLE factual claims — not opinions, not summaries.

For each claim, provide:
- text: The claim in a single clear sentence
- subject: The entity making or being described
- predicate: The action or relationship
- object: What is claimed
- claim_type: "factual" | "statistical" | "attribution" | "event"
- confidence: 0.0-1.0 (how clearly stated this is as fact)

IMPORTANT RULES:
1. Extract only claims that can be verified against evidence
2. Do NOT include opinions, speculation, or predictions as facts
3. Do NOT include claims with vague subjects ("some experts say...")
4. Keep claims atomic — one fact per claim
5. Preserve exact numbers, dates, and names
6. Return valid JSON only

Return exactly this structure:
{
  "claims": [
    {
      "text": "...",
      "subject": "...",
      "predicate": "...",
      "object": "...",
      "claim_type": "factual",
      "confidence": 0.85
    }
  ],
  "article_summary": "One sentence summary of the article",
  "primary_entities": ["Entity1", "Entity2"]
}"""


class NewsClaimAgent(BaseAgent):
    """Extracts structured factual claims from news articles using Mistral AI."""

    @property
    def agent_id(self) -> str:
        return "news-claim-agent"

    @property
    def name(self) -> str:
        return "News Claim Extraction Agent"

    @property
    def description(self) -> str:
        return "Extracts verifiable factual claims from news articles using LLM analysis."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["claim_extraction", "entity_extraction"]

    @property
    def required_permissions(self) -> list[str]:
        return ["llm"]

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        capability = task_input.capability

        if capability == "claim_extraction":
            return await self._extract_claims(task_input)
        else:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"Unknown capability: {capability}"],
            )

    async def _extract_claims(self, task_input: TaskInput) -> TaskOutput:
        article = task_input.input.get("article", {})
        title = article.get("title", "")
        content = article.get("content", "")
        article_id = article.get("article_id", "")
        event_id = task_input.input.get("event_id")

        if not content:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result={"claims": [], "reason": "Empty article content"},
                confidence=1.0,
            )

        # Truncate long articles
        max_chars = 3000
        truncated_content = content[:max_chars] + ("..." if len(content) > max_chars else "")

        prompt = f"""Article Title: {title}

Article Content:
{truncated_content}

Extract all verifiable factual claims from this article. Return only the JSON structure."""

        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=CLAIM_EXTRACTION_SYSTEM),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            # Parse LLM response
            raw_text = response.content.strip()
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_text)
            raw_claims = parsed.get("claims", [])

            # Build Claim objects
            claims: list[Claim] = []
            for raw_claim in raw_claims:
                claim = Claim(
                    event_id=event_id,
                    article_id=article_id,
                    text=raw_claim.get("text", ""),
                    subject=raw_claim.get("subject"),
                    predicate=raw_claim.get("predicate"),
                    object=raw_claim.get("object"),
                    status=ClaimStatus.UNVERIFIED,
                    confidence=float(raw_claim.get("confidence", 0.5)),
                    source_agent_id=self.agent_id,
                )
                claims.append(claim)

            # Publish event for each claim
            for claim in claims:
                await self._publisher.publish(
                    NewsClaimExtractedEvent(
                        tenant_id=task_input.tenant_id,
                        workflow_id=task_input.workflow_id,
                        producer=self.agent_id,
                        correlation_id=task_input.correlation_id,
                        payload={
                            "claim": claim.model_dump(),
                            "article_id": article_id,
                            "event_id": event_id,
                        },
                    )
                )

            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result={
                    "claims": [c.model_dump() for c in claims],
                    "claims_count": len(claims),
                    "article_summary": parsed.get("article_summary", ""),
                    "primary_entities": parsed.get("primary_entities", []),
                },
                confidence=0.85,
                token_usage={
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                },
            )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM claim response", error=str(e))
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"LLM returned invalid JSON: {e}"],
            )
        except Exception as e:
            logger.error("Claim extraction failed", error=str(e))
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[str(e)],
            )


if __name__ == "__main__":
    import asyncio
    agent = NewsClaimAgent()
    asyncio.run(agent.run())
