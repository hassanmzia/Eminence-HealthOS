"""
Eminence HealthOS — Agent Conversation Memory
Rolling-window conversation memory with LLM-summarized history compression.
Supports per-patient conversation threads with configurable window sizes.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


class ConversationMessage:
    """A single message in a conversation thread."""

    def __init__(
        self,
        role: str,  # "user", "agent", "system"
        content: str,
        agent_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.role = role
        self.content = content
        self.agent_name = agent_name
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "agent_name": self.agent_name,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class AgentMemory:
    """
    Rolling-window conversation memory for agents.

    Maintains a fixed-size window of recent messages per patient thread.
    When the window is exceeded, older messages are summarized and compressed
    to preserve context without consuming excessive token budget.
    """

    def __init__(
        self,
        window_size: int = 20,
        summary_threshold: int = 15,
    ) -> None:
        self.window_size = window_size
        self.summary_threshold = summary_threshold
        # Thread key → list of messages
        self._threads: dict[str, list[ConversationMessage]] = defaultdict(list)
        # Thread key → compressed summaries
        self._summaries: dict[str, list[str]] = defaultdict(list)
        self._log = logger.bind(component="agent_memory")

    def _thread_key(self, patient_id: str, agent_name: str = "") -> str:
        """Generate a thread key from patient and agent identifiers."""
        return f"{patient_id}:{agent_name}" if agent_name else patient_id

    def add_message(
        self,
        patient_id: str,
        role: str,
        content: str,
        agent_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to the conversation thread."""
        key = self._thread_key(patient_id, agent_name)
        message = ConversationMessage(
            role=role,
            content=content,
            agent_name=agent_name,
            metadata=metadata,
        )
        self._threads[key].append(message)

        # Check if we need to compress
        if len(self._threads[key]) > self.window_size:
            self._compress_thread(key)

    def get_history(
        self,
        patient_id: str,
        agent_name: str = "",
        include_summary: bool = True,
    ) -> list[dict[str, Any]]:
        """Get conversation history for a patient thread."""
        key = self._thread_key(patient_id, agent_name)
        messages = []

        # Include summaries of older messages
        if include_summary and key in self._summaries:
            for summary in self._summaries[key]:
                messages.append({
                    "role": "system",
                    "content": f"[Previous conversation summary]: {summary}",
                    "agent_name": "",
                    "metadata": {"is_summary": True},
                    "timestamp": "",
                })

        # Add recent messages
        for msg in self._threads.get(key, []):
            messages.append(msg.to_dict())

        return messages

    def get_context_window(
        self,
        patient_id: str,
        agent_name: str = "",
        max_messages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get the most recent messages within the context window."""
        key = self._thread_key(patient_id, agent_name)
        messages = self._threads.get(key, [])
        limit = max_messages or self.window_size
        return [msg.to_dict() for msg in messages[-limit:]]

    def clear_thread(self, patient_id: str, agent_name: str = "") -> None:
        """Clear a conversation thread."""
        key = self._thread_key(patient_id, agent_name)
        self._threads.pop(key, None)
        self._summaries.pop(key, None)

    def _compress_thread(self, key: str) -> None:
        """Compress older messages by summarizing them."""
        messages = self._threads[key]

        # Take the oldest messages beyond the threshold
        to_compress = messages[: len(messages) - self.summary_threshold]
        to_keep = messages[len(messages) - self.summary_threshold :]

        if not to_compress:
            return

        # Generate summary (simple concatenation — in production use LLM)
        summary_parts = []
        for msg in to_compress:
            summary_parts.append(f"{msg.role}: {msg.content[:100]}")

        summary = f"Conversation summary ({len(to_compress)} messages): " + "; ".join(
            summary_parts[:5]
        )

        self._summaries[key].append(summary)
        self._threads[key] = to_keep

        self._log.info(
            "memory.compressed",
            thread=key,
            compressed=len(to_compress),
            remaining=len(to_keep),
            total_summaries=len(self._summaries[key]),
        )

    async def summarize_with_llm(self, key: str) -> str | None:
        """Use LLM to generate a high-quality summary of compressed messages."""
        try:
            from healthos_platform.ml.llm.client import get_llm_client

            messages = self._threads.get(key, [])
            if not messages:
                return None

            transcript = "\n".join(
                f"{msg.role} ({msg.agent_name}): {msg.content}" for msg in messages
            )

            client = get_llm_client()
            summary = await client.generate(
                f"Summarize this clinical conversation concisely, preserving key "
                f"medical decisions, findings, and action items:\n\n{transcript}"
            )
            return summary
        except Exception as e:
            self._log.warning("memory.llm_summary_failed", error=str(e))
            return None

    @property
    def thread_count(self) -> int:
        return len(self._threads)


# Module-level singleton
agent_memory = AgentMemory()
