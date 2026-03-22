"""
LLM Abstraction Layer
Supports multiple LLM providers: Claude (Anthropic), Ollama (local), OpenAI
Provides unified interface for clinical reasoning with logging and tracing.
"""

import os
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class LLMProvider(Enum):
    CLAUDE = "claude"
    OLLAMA = "ollama"
    OPENAI = "openai"


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    provider: LLMProvider = LLMProvider.CLAUDE

    # Claude settings
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Ollama settings (local Deepseek-r1)
    ollama_base_url: str = "http://localhost:12434"
    ollama_model: str = "deepseek-r1:7b"

    # OpenAI settings (optional)
    openai_api_key: str = ""
    openai_model: str = "gpt-4"

    # Common settings
    max_tokens: int = 2000
    temperature: float = 0.3  # Lower for more deterministic clinical outputs
    timeout: int = 60

    # Guardrails
    enable_content_filter: bool = True
    enable_medical_disclaimer: bool = True
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables"""
        provider_str = os.getenv("LLM_PROVIDER", "claude").lower()
        provider = LLMProvider(provider_str) if provider_str in [p.value for p in LLMProvider] else LLMProvider.CLAUDE

        return cls(
            provider=provider,
            claude_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:12434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "deepseek-r1:7b"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        )


# ============================================================================
# Tracing and Logging
# ============================================================================

@dataclass
class LLMTrace:
    """Trace record for LLM calls - for debugging and audit"""
    trace_id: str
    timestamp: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0
    success: bool = True
    error: Optional[str] = None

    # Input/Output (sanitized - no PHI in production)
    prompt_preview: str = ""  # First 200 chars
    response_preview: str = ""  # First 200 chars

    # Clinical context
    patient_id: Optional[str] = None
    task_type: Optional[str] = None  # diagnosis, treatment, etc.

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "tokens": {"prompt": self.prompt_tokens, "completion": self.completion_tokens},
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error,
            "task_type": self.task_type
        }


class LLMTracer:
    """Manages LLM call tracing for observability"""

    def __init__(self):
        self.traces: List[LLMTrace] = []
        self.max_traces = 1000  # Keep last 1000 traces in memory

    def start_trace(self, provider: str, model: str, task_type: str = None, patient_id: str = None) -> LLMTrace:
        trace = LLMTrace(
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            provider=provider,
            model=model,
            task_type=task_type,
            patient_id=patient_id
        )
        return trace

    def end_trace(self, trace: LLMTrace, success: bool, error: str = None):
        trace.success = success
        trace.error = error
        self.traces.append(trace)

        # Log trace
        if success:
            logger.info(f"LLM Trace: {trace.trace_id} | {trace.provider}/{trace.model} | {trace.latency_ms:.0f}ms | {trace.task_type}")
        else:
            logger.error(f"LLM Trace FAILED: {trace.trace_id} | {trace.provider}/{trace.model} | {error}")

        # Cleanup old traces
        if len(self.traces) > self.max_traces:
            self.traces = self.traces[-self.max_traces:]

    def get_recent_traces(self, limit: int = 100) -> List[dict]:
        return [t.to_dict() for t in self.traces[-limit:]]


# Global tracer instance
tracer = LLMTracer()


# ============================================================================
# Medical Prompting
# ============================================================================

MEDICAL_SYSTEM_PROMPT = """You are an AI clinical decision support assistant. Your role is to help healthcare providers by analyzing patient data and providing evidence-based recommendations.

IMPORTANT GUIDELINES:
1. Always provide ICD-10 codes for diagnoses and CPT codes for procedures when applicable
2. Base recommendations on current clinical guidelines (ACC/AHA, ADA, GOLD, etc.)
3. Consider patient-specific factors: age, comorbidities, medications, allergies
4. Flag critical findings that require immediate attention
5. Acknowledge uncertainty - provide confidence levels for diagnoses
6. Never make definitive diagnoses - these are recommendations for clinician review

RESPONSE FORMAT:
- Be structured and concise
- Use medical terminology appropriately
- Include evidence/rationale for recommendations
- Format output as JSON when requested

LIMITATIONS:
- This is a decision support tool, not a replacement for clinical judgment
- All recommendations require physician review and approval
- Patient should be evaluated in person for final diagnosis"""

ANTI_HALLUCINATION_PROMPT = """
IMPORTANT - ACCURACY REQUIREMENTS:
- Only cite ICD-10/CPT codes that you are confident exist
- If unsure about a specific code, indicate uncertainty
- Base clinical thresholds on established guidelines
- Do not invent drug names, dosages, or interactions
- If information is insufficient, state what additional data is needed
- Distinguish between findings (observed) and impressions (interpreted)
"""


# ============================================================================
# Base LLM Client
# ============================================================================

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.tracer = tracer

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        task_type: str = None,
        patient_id: str = None,
        json_mode: bool = False
    ) -> dict:
        """
        Generate response from LLM

        Returns:
            dict with keys: content, usage, model, provider
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this LLM provider is available"""
        pass

    def _get_system_prompt(self, custom_system: str = None) -> str:
        """Build system prompt with guardrails"""
        base = MEDICAL_SYSTEM_PROMPT
        if self.config.enable_content_filter:
            base += "\n" + ANTI_HALLUCINATION_PROMPT
        if custom_system:
            base += "\n\n" + custom_system
        return base


# ============================================================================
# Claude Client
# ============================================================================

class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API client"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.claude_api_key
        self.model = config.claude_model
        self.base_url = "https://api.anthropic.com/v1"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        task_type: str = None,
        patient_id: str = None,
        json_mode: bool = False
    ) -> dict:
        if not self.is_available():
            raise ValueError("Claude API key not configured")

        trace = self.tracer.start_trace("claude", self.model, task_type, patient_id)
        trace.prompt_preview = prompt[:200]
        start_time = time.time()

        system = self._get_system_prompt(system_prompt)
        if json_mode:
            system += "\n\nRespond with valid JSON only."

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": self.config.max_tokens,
                        "temperature": self.config.temperature,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                response.raise_for_status()
                data = response.json()

            content = data["content"][0]["text"]
            usage = data.get("usage", {})

            trace.latency_ms = (time.time() - start_time) * 1000
            trace.prompt_tokens = usage.get("input_tokens", 0)
            trace.completion_tokens = usage.get("output_tokens", 0)
            trace.response_preview = content[:200]
            self.tracer.end_trace(trace, success=True)

            return {
                "content": content,
                "usage": usage,
                "model": self.model,
                "provider": "claude"
            }

        except Exception as e:
            trace.latency_ms = (time.time() - start_time) * 1000
            self.tracer.end_trace(trace, success=False, error=str(e))
            raise


# ============================================================================
# Ollama Client (Local Deepseek-r1)
# ============================================================================

class OllamaClient(BaseLLMClient):
    """Ollama local LLM client (Deepseek-r1, Llama, etc.)"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model

    def is_available(self) -> bool:
        """Check if Ollama server is running"""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        task_type: str = None,
        patient_id: str = None,
        json_mode: bool = False
    ) -> dict:
        trace = self.tracer.start_trace("ollama", self.model, task_type, patient_id)
        trace.prompt_preview = prompt[:200]
        start_time = time.time()

        system = self._get_system_prompt(system_prompt)
        if json_mode:
            system += "\n\nRespond with valid JSON only."

        # Combine system and user prompt for Ollama
        full_prompt = f"{system}\n\nUser: {prompt}\n\nAssistant:"

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()

            content = data.get("response", "")

            trace.latency_ms = (time.time() - start_time) * 1000
            trace.prompt_tokens = data.get("prompt_eval_count", 0)
            trace.completion_tokens = data.get("eval_count", 0)
            trace.response_preview = content[:200]
            self.tracer.end_trace(trace, success=True)

            return {
                "content": content,
                "usage": {
                    "prompt_tokens": trace.prompt_tokens,
                    "completion_tokens": trace.completion_tokens
                },
                "model": self.model,
                "provider": "ollama"
            }

        except Exception as e:
            trace.latency_ms = (time.time() - start_time) * 1000
            self.tracer.end_trace(trace, success=False, error=str(e))
            raise


# ============================================================================
# OpenAI Client (ChatGPT)
# ============================================================================

class OpenAIClient(BaseLLMClient):
    """OpenAI ChatGPT API client"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.openai_api_key
        self.model = config.openai_model
        self.base_url = "https://api.openai.com/v1"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        task_type: str = None,
        patient_id: str = None,
        json_mode: bool = False
    ) -> dict:
        if not self.is_available():
            raise ValueError("OpenAI API key not configured")

        trace = self.tracer.start_trace("openai", self.model, task_type, patient_id)
        trace.prompt_preview = prompt[:200]
        start_time = time.time()

        system = self._get_system_prompt(system_prompt)
        if json_mode:
            system += "\n\nRespond with valid JSON only."

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        body: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": messages,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            trace.latency_ms = (time.time() - start_time) * 1000
            trace.prompt_tokens = usage.get("prompt_tokens", 0)
            trace.completion_tokens = usage.get("completion_tokens", 0)
            trace.response_preview = content[:200]
            self.tracer.end_trace(trace, success=True)

            return {
                "content": content,
                "usage": usage,
                "model": self.model,
                "provider": "openai",
            }

        except Exception as e:
            trace.latency_ms = (time.time() - start_time) * 1000
            self.tracer.end_trace(trace, success=False, error=str(e))
            raise


# ============================================================================
# Unified LLM Interface
# ============================================================================

class ClinicalLLM:
    """
    Unified interface for clinical LLM operations.
    Supports fallback between providers.
    """

    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig.from_env()

        # Initialize clients
        self.clients: Dict[LLMProvider, BaseLLMClient] = {}

        self.clients[LLMProvider.CLAUDE] = ClaudeClient(self.config)
        self.clients[LLMProvider.OLLAMA] = OllamaClient(self.config)
        self.clients[LLMProvider.OPENAI] = OpenAIClient(self.config)

        # Set primary provider
        self.primary_provider = self.config.provider

        logger.info(f"ClinicalLLM initialized with primary provider: {self.primary_provider.value}")

    def get_available_providers(self) -> List[str]:
        """List available LLM providers"""
        return [p.value for p, c in self.clients.items() if c.is_available()]

    def set_provider(self, provider: str):
        """Switch primary provider"""
        self.primary_provider = LLMProvider(provider)
        logger.info(f"Switched primary provider to: {provider}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        task_type: str = None,
        patient_id: str = None,
        json_mode: bool = False,
        fallback: bool = True
    ) -> dict:
        """
        Generate LLM response with optional fallback.

        Args:
            prompt: User prompt
            system_prompt: Additional system instructions
            task_type: Type of clinical task (diagnosis, treatment, etc.)
            patient_id: Patient ID for tracing
            json_mode: Request JSON output
            fallback: Try other providers if primary fails

        Returns:
            dict with content, usage, model, provider
        """
        # Try primary provider
        primary_client = self.clients.get(self.primary_provider)

        if primary_client and primary_client.is_available():
            try:
                return await primary_client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type=task_type,
                    patient_id=patient_id,
                    json_mode=json_mode
                )
            except Exception as e:
                logger.warning(f"Primary provider {self.primary_provider.value} failed: {e}")
                if not fallback:
                    raise

        # Fallback to other providers
        if fallback:
            for provider, client in self.clients.items():
                if provider != self.primary_provider and client.is_available():
                    try:
                        logger.info(f"Falling back to {provider.value}")
                        return await client.generate(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            task_type=task_type,
                            patient_id=patient_id,
                            json_mode=json_mode
                        )
                    except Exception as e:
                        logger.warning(f"Fallback provider {provider.value} failed: {e}")
                        continue

        raise RuntimeError("No LLM providers available")

    async def clinical_reasoning(
        self,
        task: str,
        patient_data: dict,
        output_format: str = "json"
    ) -> dict:
        """
        High-level clinical reasoning method.

        Args:
            task: What to analyze (diagnosis, treatment, labs, etc.)
            patient_data: Patient context dictionary
            output_format: json or text

        Returns:
            Parsed clinical response
        """
        prompt = f"""
Task: {task}

Patient Data:
{json.dumps(patient_data, indent=2)}

Provide your clinical analysis following the established guidelines.
"""

        response = await self.generate(
            prompt=prompt,
            task_type=task,
            patient_id=patient_data.get("patient_id"),
            json_mode=(output_format == "json")
        )

        content = response["content"]

        # Try to parse JSON if requested
        if output_format == "json":
            try:
                # Extract JSON from response
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    return {
                        "result": json.loads(content[start:end]),
                        "raw": content,
                        "provider": response["provider"],
                        "model": response["model"]
                    }
            except json.JSONDecodeError:
                pass

        return {
            "result": content,
            "raw": content,
            "provider": response["provider"],
            "model": response["model"]
        }

    def get_traces(self, limit: int = 100) -> List[dict]:
        """Get recent LLM call traces"""
        return tracer.get_recent_traces(limit)


# ============================================================================
# Singleton instance
# ============================================================================

_llm_instance: Optional[ClinicalLLM] = None


def get_clinical_llm() -> ClinicalLLM:
    """Get or create the global ClinicalLLM instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ClinicalLLM()
    return _llm_instance


def configure_llm(config: LLMConfig):
    """Configure the global LLM instance"""
    global _llm_instance
    _llm_instance = ClinicalLLM(config)
    return _llm_instance
