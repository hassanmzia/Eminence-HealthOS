"""
Eminence HealthOS — LLM Provider Router
Provider-agnostic interface for LLM calls. Swap models per agent without code changes.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import structlog
from pydantic import BaseModel, Field

from healthos_platform.config import get_settings

logger = structlog.get_logger()


class LLMRequest(BaseModel):
    """Standard request to any LLM provider."""

    messages: list[dict[str, str]]
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096
    system: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Standard response from any LLM provider."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] = Field(default_factory=dict)  # input_tokens, output_tokens
    finish_reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def health_check(self) -> bool: ...


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    provider_name = "anthropic"

    def __init__(self) -> None:
        try:
            import anthropic
            settings = get_settings()
            self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.default_model = settings.default_llm_model
        except ImportError:
            logger.warning("llm.anthropic.not_installed")
            self.client = None
            self.default_model = "claude-sonnet-4-20250514"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if self.client is None:
            raise RuntimeError("anthropic package not installed")

        model = request.model or self.default_model
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": request.messages,
        }
        if request.system:
            kwargs["system"] = request.system

        response = await self.client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text if response.content else "",
            model=model,
            provider=self.provider_name,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason or "",
        )

    async def health_check(self) -> bool:
        return self.client is not None


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider for PHI-sensitive operations."""

    provider_name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.default_model = "llama3.2"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        import httpx

        model = request.model or self.default_model

        # Convert messages to Ollama format
        prompt_parts = []
        if request.system:
            prompt_parts.append(f"System: {request.system}")
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role.capitalize()}: {content}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "\n\n".join(prompt_parts),
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            content=data.get("response", ""),
            model=model,
            provider=self.provider_name,
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
            finish_reason="stop",
        )

    async def health_check(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


class LLMRouter:
    """
    Routes LLM requests to the appropriate provider.
    Supports fallback chains: if the primary provider fails, try the next.
    """

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._default_provider: str = ""
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        settings = get_settings()

        # Register Anthropic if API key is available
        if settings.anthropic_api_key:
            self._providers["anthropic"] = AnthropicProvider()

        # Always register Ollama (local, no key needed)
        self._providers["ollama"] = OllamaProvider()

        self._default_provider = settings.default_llm_provider

        logger.info(
            "llm.router.initialized",
            providers=list(self._providers.keys()),
            default=self._default_provider,
        )

    async def complete(
        self,
        request: LLMRequest,
        provider: str | None = None,
        fallback_providers: list[str] | None = None,
    ) -> LLMResponse:
        """
        Send a completion request to an LLM provider.
        Falls back through providers on failure.
        """
        target = provider or self._default_provider
        providers_to_try = [target]

        if fallback_providers:
            providers_to_try.extend(fallback_providers)

        last_error: Exception | None = None

        for p in providers_to_try:
            llm = self._providers.get(p)
            if llm is None:
                continue

            try:
                response = await llm.complete(request)
                logger.info(
                    "llm.request.success",
                    provider=p,
                    model=response.model,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                )
                return response
            except Exception as exc:
                logger.warning("llm.request.failed", provider=p, error=str(exc))
                last_error = exc

        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        )

    def get_provider(self, name: str) -> LLMProvider | None:
        return self._providers.get(name)

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers.keys())


# Module-level singleton
llm_router = LLMRouter()
