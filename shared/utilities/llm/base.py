"""
AgentOS LLM abstraction — base interface.
All provider adapters must implement LLMProvider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: MessageRole
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cost_usd(self) -> Optional[float]:
        """Cost estimate — override per provider."""
        return None


class LLMProvider(ABC):
    """Abstract LLM provider interface. Swap implementations via factory."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def complete_simple(
        self,
        prompt: str,
        system: str = "You are a helpful AI assistant.",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Convenience wrapper for a single prompt."""
        return await self.complete(
            messages=[
                Message(role=MessageRole.SYSTEM, content=system),
                Message(role=MessageRole.USER, content=prompt),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
