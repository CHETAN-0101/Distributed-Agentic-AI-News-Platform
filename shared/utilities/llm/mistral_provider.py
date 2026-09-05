"""
AgentOS — Mistral AI provider adapter.
"""
from __future__ import annotations

from typing import Any

import httpx

from shared.config import settings
from shared.logging import get_logger
from shared.utilities.llm.base import LLMProvider, LLMResponse, Message, MessageRole

logger = get_logger(__name__)


class MistralProvider(LLMProvider):
    """Mistral AI adapter using the Mistral REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ):
        self._api_key = api_key or settings.mistral_api_key
        self._model = model or settings.mistral_model
        self._base_url = (base_url or settings.mistral_base_url).rstrip("/")
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )

    @property
    def provider_name(self) -> str:
        return "mistral"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[Message],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Mistral API error",
                status_code=e.response.status_code,
                body=e.response.text,
            )
            raise

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self._model),
            provider="mistral",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Mistral Embed."""
        payload = {
            "model": settings.embedding_model,
            "input": texts,
        }
        response = await self._client.post("/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def close(self) -> None:
        await self._client.aclose()
