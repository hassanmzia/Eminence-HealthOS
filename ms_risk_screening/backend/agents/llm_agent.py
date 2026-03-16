"""LLM-powered agent capabilities for enhanced analysis."""
import logging
import os
from typing import Optional
from django.conf import settings

logger = logging.getLogger('agents')


def get_llm_client():
    """Get OpenAI-compatible client if API key is configured."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None
    try:
        from openai import OpenAI
        kwargs = {'api_key': api_key}
        if settings.OPENAI_BASE_URL:
            kwargs['base_url'] = settings.OPENAI_BASE_URL
        return OpenAI(**kwargs)
    except Exception as e:
        logger.warning(f"Failed to initialize LLM client: {e}")
        return None


def llm_call(prompt: str, model: Optional[str] = None,
             temperature: float = 0.2, max_tokens: int = 400) -> str:
    """Generic LLM completion call with graceful fallback."""
    client = get_llm_client()
    if not client:
        return "[LLM not configured - set OPENAI_API_KEY]"
    try:
        resp = client.chat.completions.create(
            model=model or settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a careful clinical assistant. Be concise and explicit about uncertainty."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"[LLM error: {e}]"


def llm_summarize_note(note_text: str) -> str:
    """Summarize a clinical note excerpt for clinician review."""
    prompt = (
        f"Summarize this synthetic clinical note excerpt for a neurologist reviewing MS risk:\n\n"
        f"\"{note_text}\"\n\n"
        f"In <=3 bullet points, note:\n"
        f"1. Evidence suggestive of demyelinating disease / MS\n"
        f"2. Plausible alternative explanations\n"
        f"3. Missing information that would be needed"
    )
    return llm_call(prompt, max_tokens=250)


def llm_patient_card_explanation(card: dict) -> str:
    """Generate a clinician-facing explanation of a patient risk card."""
    prompt = (
        f"Given this patient risk assessment card:\n{card}\n\n"
        f"Provide:\n"
        f"1. A 2-4 sentence explanation of why this patient was flagged\n"
        f"2. 2 recommended next steps\n"
        f"3. 1 caution about automation overreliance"
    )
    return llm_call(prompt, max_tokens=300)


def llm_propose_thresholds(current_metrics: str) -> str:
    """Propose policy threshold adjustments (teaching/advisory only)."""
    prompt = (
        f"Current screening metrics:\n{current_metrics}\n\n"
        f"Propose:\n"
        f"1. Revised thresholds (review, draft, auto)\n"
        f"2. Justification\n"
        f"3. 2 risks of aggressive threshold changes\n"
        f"NOTE: This is for teaching purposes only and must be validated offline."
    )
    return llm_call(prompt, max_tokens=300)
