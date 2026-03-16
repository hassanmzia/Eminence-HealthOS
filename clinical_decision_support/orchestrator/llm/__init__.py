"""
LLM Abstraction Layer for Clinical AI
Supports Claude (Anthropic), Ollama (local Deepseek-r1), and OpenAI
"""

from .clinical_llm import (
    ClinicalLLM,
    LLMConfig,
    LLMProvider,
    ClaudeClient,
    OllamaClient,
    BaseLLMClient,
    LLMTrace,
    LLMTracer,
    get_clinical_llm,
    configure_llm,
    tracer,
    MEDICAL_SYSTEM_PROMPT,
    ANTI_HALLUCINATION_PROMPT,
)

__all__ = [
    "ClinicalLLM",
    "LLMConfig",
    "LLMProvider",
    "ClaudeClient",
    "OllamaClient",
    "BaseLLMClient",
    "LLMTrace",
    "LLMTracer",
    "get_clinical_llm",
    "configure_llm",
    "tracer",
    "MEDICAL_SYSTEM_PROMPT",
    "ANTI_HALLUCINATION_PROMPT",
]
