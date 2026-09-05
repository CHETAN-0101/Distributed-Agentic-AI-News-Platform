"""
AgentOS — LLM provider factory.
Reads LLM_PROVIDER env var and returns the appropriate adapter.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from shared.config import settings
from shared.logging import get_logger
from shared.utilities.llm.base import LLMProvider

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm_provider(provider: Optional[str] = None) -> LLMProvider:
    """
    Return the configured LLM provider singleton.

    Priority:
        1. provider argument
        2. LLM_PROVIDER env var (settings.llm_provider)
        3. Defaults to Mistral
    """
    p = (provider or settings.llm_provider).lower()
    logger.info("Initializing LLM provider", provider=p)

    if p == "mistral":
        from shared.utilities.llm.mistral_provider import MistralProvider
        return MistralProvider()

    elif p == "openai":
        from shared.utilities.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()

    elif p == "ollama":
        from shared.utilities.llm.ollama_provider import OllamaProvider
        return OllamaProvider()

    else:
        raise ValueError(f"Unknown LLM provider: '{p}'. Choose from: mistral, openai, ollama")


@lru_cache(maxsize=1)
def get_embedding_provider() -> LLMProvider:
    """Return the configured embedding provider (may differ from chat provider)."""
    return get_llm_provider(settings.embedding_provider)
