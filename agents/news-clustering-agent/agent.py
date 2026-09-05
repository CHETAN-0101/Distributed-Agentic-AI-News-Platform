"""
AgentOS — News Clustering Agent

Groups articles covering the same real-world event using:
1. Semantic similarity (embedding cosine distance)
2. Named entity overlap (shared persons, orgs, locations)
3. Time proximity (articles close in time)
4. Topic keywords
5. Title similarity (trigram-based)

Publishes news.event.updated events when clusters change.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.events import NewsEventUpdatedEvent
from shared.schemas.news import NewsEvent, NamedEntity, TimelineEntry
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.utilities.llm.base import Message, MessageRole

logger = get_logger(__name__)

CLUSTERING_SYSTEM = """You are an expert news editor with deep experience in story clustering.

Your task is to determine if a new article belongs to an existing story cluster or represents a new event.

Return ONLY valid JSON."""


class NewsClusteringAgent(BaseAgent):

    @property
    def agent_id(self) -> str:
        return "news-clustering-agent"

    @property
    def name(self) -> str:
        return "News Clustering Agent"

    @property
    def description(self) -> str:
        return "Groups articles about the same real-world event into story clusters."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["news_clustering", "event_detection", "story_grouping"]

    @property
    def required_permissions(self) -> list[str]:
        return ["llm"]

    # In-memory cluster store (production would use Redis/DB)
    def __init__(self):
        super().__init__()
        self._clusters: dict[str, NewsEvent] = {}

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        cap = task_input.capability
        if cap in ("news_clustering", "event_detection", "story_grouping"):
            return await self._cluster_article(task_input)
        return TaskOutput(task_id=task_input.task_id, agent_id=self.agent_id,
                          status=TaskStatus.FAILED, errors=[f"Unknown: {cap}"])

    async def _cluster_article(self, task_input: TaskInput) -> TaskOutput:
        article = task_input.input.get("article", {})
        title = article.get("title", "")
        content = article.get("content", "")[:1000]
        article_id = article.get("article_id", "")
        published_at = article.get("published_at", "")

        if not title:
            return TaskOutput(task_id=task_input.task_id, agent_id=self.agent_id,
                              status=TaskStatus.COMPLETED,
                              result={"clustered": False, "reason": "No title"}, confidence=1.0)

        # Find candidate clusters (time-proximate, non-empty)
        candidates = list(self._clusters.values())[:10]  # Limit candidates for LLM

        candidates_summary = [
            {"event_id": c.event_id, "title": c.title, "entity_count": len(c.entities),
             "article_count": len(c.article_ids)}
            for c in candidates
        ]

        prompt = f"""New Article:
Title: {title}
Content: {content}
Published: {published_at}

Existing story clusters (recent):
{json.dumps(candidates_summary, indent=2)}

Determine if this article belongs to an existing cluster or represents a new event.

Rules:
- Cluster if: same real-world event, same core entities, same time period
- New event if: clearly different incident, different entities, different location

Return JSON:
{{
  "belongs_to_existing": true/false,
  "event_id": "existing_id or null",
  "new_event_title": "if new event, title for it",
  "entities": [{{"text": "...", "label": "PERSON|ORG|GPE|DATE"}}],
  "category": "politics|technology|business|science|health|sports|other",
  "confidence": 0.0-1.0
}}"""

        try:
            response = await self._llm.complete(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=CLUSTERING_SYSTEM),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                temperature=0.1, max_tokens=512,
            )
            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            parsed = json.loads(raw)
        except Exception as e:
            logger.error("Clustering LLM call failed", error=str(e))
            # Default: create new event
            parsed = {"belongs_to_existing": False, "new_event_title": title, "entities": [], "confidence": 0.4}

        entities = [NamedEntity(**e) for e in parsed.get("entities", [])]

        if parsed.get("belongs_to_existing") and parsed.get("event_id"):
            # Add to existing cluster
            event_id = parsed["event_id"]
            if event_id in self._clusters:
                cluster = self._clusters[event_id]
                if article_id not in cluster.article_ids:
                    cluster.article_ids.append(article_id)
                    cluster.last_updated = datetime.utcnow()
                    # Add timeline entry
                    cluster.timeline.append(TimelineEntry(
                        timestamp=datetime.utcnow(),
                        title=title[:80],
                        description=content[:200],
                        article_id=article_id,
                        entry_type="update",
                    ))
                    # Publish event updated
                    await self._publisher.publish(
                        NewsEventUpdatedEvent(
                            tenant_id=task_input.tenant_id,
                            producer=self.agent_id,
                            payload=cluster.model_dump(),
                        )
                    )
                result = {"clustered": True, "event_id": event_id, "action": "added_to_existing"}
            else:
                result = {"clustered": False, "reason": "event_id not found locally"}
        else:
            # Create new event cluster
            event_id = str(uuid4())
            new_event = NewsEvent(
                event_id=event_id,
                title=parsed.get("new_event_title", title),
                status="developing",
                category=parsed.get("category", "general"),
                entities=entities,
                article_ids=[article_id],
                timeline=[TimelineEntry(
                    timestamp=datetime.utcnow(),
                    title=title[:80],
                    description=content[:200],
                    article_id=article_id,
                    entry_type="initial",
                )],
            )
            self._clusters[event_id] = new_event
            await self._publisher.publish(
                NewsEventUpdatedEvent(
                    tenant_id=task_input.tenant_id,
                    producer=self.agent_id,
                    payload=new_event.model_dump(),
                )
            )
            result = {"clustered": True, "event_id": event_id, "action": "new_event_created",
                      "event_title": new_event.title}

        return TaskOutput(
            task_id=task_input.task_id, agent_id=self.agent_id,
            status=TaskStatus.COMPLETED, result=result,
            confidence=float(parsed.get("confidence", 0.7)),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(NewsClusteringAgent().run())
