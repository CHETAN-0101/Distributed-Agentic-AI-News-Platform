"""
AgentOS — News Ingestion Agent

Capabilities:
- Fetches articles from RSS feeds and news APIs
- Normalizes to standard NewsArticle schema
- Deduplicates against seen article IDs
- Publishes news.article.ingested events
- Runs on a schedule AND on-demand
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import aiohttp
import feedparser

from agents.base import BaseAgent
from shared.logging import get_logger
from shared.schemas.events import NewsArticleIngestedEvent
from shared.schemas.news import NewsArticle, NamedEntity
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus

logger = get_logger(__name__)

# -------------------------------------------------------------------------
# RSS Feed Sources
# -------------------------------------------------------------------------
DEFAULT_RSS_FEEDS = [
    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "category": "general"},
    {"name": "Reuters", "url": "https://feeds.reuters.com/reuters/topNews", "category": "general"},
    {"name": "AP News", "url": "https://feeds.apnews.com/ApNewsAlert", "category": "general"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss", "category": "world"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "world"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "technology"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "technology"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": "technology"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "category": "technology"},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "category": "technology"},
    {"name": "BBC Business", "url": "http://feeds.bbci.co.uk/news/business/rss.xml", "category": "business"},
    {"name": "BBC Science", "url": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "category": "science"},
]


class NewsIngestionAgent(BaseAgent):
    """Fetches, normalizes, and publishes news articles from RSS feeds."""

    @property
    def agent_id(self) -> str:
        return "news-ingestion-agent"

    @property
    def name(self) -> str:
        return "News Ingestion Agent"

    @property
    def description(self) -> str:
        return "Fetches articles from RSS feeds and news APIs, normalizes them, and publishes ingestion events."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        return ["news_ingestion", "rss_fetch", "article_normalize"]

    @property
    def required_permissions(self) -> list[str]:
        return ["internet"]

    def __init__(self) -> None:
        super().__init__()
        self._seen_ids: set[str] = set()  # In-memory dedup; backed by Redis in production
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._ingestion_interval = 300  # seconds

    async def startup(self) -> None:
        self._http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "AgentOS/1.0 News Ingestion Bot (contact: admin@agentos.local)"},
        )
        await super().startup()

        # Start the scheduled ingestion loop
        asyncio.create_task(self._scheduled_ingestion_loop())

    async def shutdown(self) -> None:
        if self._http_session:
            await self._http_session.close()
        await super().shutdown()

    async def execute(self, task_input: TaskInput) -> TaskOutput:
        """Handle on-demand ingestion requests."""
        capability = task_input.capability

        if capability == "rss_fetch":
            feeds = task_input.input.get("feeds", DEFAULT_RSS_FEEDS)
            articles = await self._ingest_feeds(feeds)
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result={"articles_ingested": len(articles), "articles": [a.model_dump() for a in articles]},
                confidence=1.0,
            )

        elif capability == "article_normalize":
            raw = task_input.input.get("article", {})
            article = self._normalize_raw(raw)
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                result=article.model_dump(),
                confidence=0.95,
            )

        else:
            return TaskOutput(
                task_id=task_input.task_id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                errors=[f"Unknown capability: {capability}"],
            )

    # -------------------------------------------------------------------------
    # Scheduled ingestion
    # -------------------------------------------------------------------------
    async def _scheduled_ingestion_loop(self) -> None:
        """Run ingestion on schedule."""
        logger.info("Scheduled ingestion started", interval_s=self._ingestion_interval)
        while self._running:
            try:
                articles = await self._ingest_feeds(DEFAULT_RSS_FEEDS)
                logger.info("Scheduled ingestion completed", count=len(articles))
            except Exception as e:
                logger.error("Scheduled ingestion failed", error=str(e))

            await asyncio.sleep(self._ingestion_interval)

    async def _ingest_feeds(self, feeds: list[dict]) -> list[NewsArticle]:
        """Fetch and process all feeds concurrently."""
        tasks = [self._fetch_feed(feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[NewsArticle] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Feed fetch error", error=str(result))
            elif isinstance(result, list):
                all_articles.extend(result)

        return all_articles

    async def _fetch_feed(self, feed_config: dict) -> list[NewsArticle]:
        """Fetch a single RSS feed and return normalized articles."""
        url = feed_config["url"]
        feed_name = feed_config.get("name", url)
        category = feed_config.get("category", "general")

        try:
            # feedparser is synchronous; run in executor
            loop = asyncio.get_event_loop()
            parsed = await loop.run_in_executor(None, feedparser.parse, url)

            if parsed.bozo and parsed.bozo_exception:
                logger.warning("Feed parse warning", feed=feed_name, error=str(parsed.bozo_exception))

            articles = []
            for entry in parsed.entries[:20]:  # max 20 per feed per run
                article = self._parse_entry(entry, feed_name, category)
                if article and article.article_id not in self._seen_ids:
                    self._seen_ids.add(article.article_id)
                    await self._publish_article(article)
                    articles.append(article)

            logger.debug("Feed fetched", feed=feed_name, new_articles=len(articles))
            return articles

        except Exception as e:
            logger.error("Failed to fetch feed", feed=feed_name, url=url, error=str(e))
            return []

    def _parse_entry(self, entry: Any, source: str, category: str) -> Optional[NewsArticle]:
        """Parse a single feed entry into a normalized NewsArticle."""
        try:
            title = entry.get("title", "").strip()
            url = entry.get("link", "")
            content = (
                entry.get("summary", "")
                or entry.get("content", [{}])[0].get("value", "")
                if entry.get("content")
                else entry.get("summary", "")
            )

            # Clean HTML tags from content
            content = re.sub(r"<[^>]+>", " ", content).strip()

            if not title or not url:
                return None

            # Generate stable article_id from URL
            article_id = hashlib.md5(url.encode()).hexdigest()

            # Parse date
            published_at = None
            if entry.get("published_parsed"):
                import time
                published_at = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed), tz=timezone.utc
                )

            author = entry.get("author", "") or ""
            if hasattr(entry, "authors") and entry.authors:
                author = ", ".join(a.get("name", "") for a in entry.authors if a.get("name"))

            return NewsArticle(
                article_id=article_id,
                title=title,
                content=content or title,
                source=source,
                source_type="rss",
                author=author or None,
                published_at=published_at,
                url=url,
                language="en",
                category=category,
                word_count=len(content.split()) if content else 0,
                metadata={"feed_source": source},
            )
        except Exception as e:
            logger.warning("Entry parse error", error=str(e))
            return None

    def _normalize_raw(self, raw: dict) -> NewsArticle:
        """Normalize a raw article dict to NewsArticle schema."""
        return NewsArticle(
            article_id=raw.get("article_id") or hashlib.md5(raw.get("url", str(uuid4())).encode()).hexdigest(),
            title=raw.get("title", "Untitled"),
            content=raw.get("content", ""),
            source=raw.get("source", "unknown"),
            source_type=raw.get("source_type", "news"),
            author=raw.get("author"),
            url=raw.get("url", ""),
            language=raw.get("language", "en"),
            category=raw.get("category"),
        )

    async def _publish_article(self, article: NewsArticle) -> None:
        """Publish news.article.ingested event to RabbitMQ."""
        event = NewsArticleIngestedEvent(
            tenant_id="default",
            producer=self.agent_id,
            payload=article.model_dump(),
        )
        await self._publisher.publish(event)
        logger.debug("Article published", article_id=article.article_id, title=article.title[:60])


# -------------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    agent = NewsIngestionAgent()

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        pass
