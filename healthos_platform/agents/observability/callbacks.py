"""
Callback handlers for LangSmith and Langfuse integration.
Captures LLM, chain, tool, and agent interactions for tracing.
"""

import os
from typing import List, Any
from langchain_core.callbacks import BaseCallbackHandler


def get_langsmith_callbacks() -> List[BaseCallbackHandler]:
    """Get LangSmith callback handlers if enabled."""
    # LangSmith auto-configures via LANGCHAIN_TRACING_V2=true
    return []


def get_langfuse_callbacks() -> List[BaseCallbackHandler]:
    """Get Langfuse callback handlers if enabled."""
    callbacks = []

    if os.environ.get("LANGFUSE_PUBLIC_KEY"):
        try:
            from langfuse.callback import CallbackHandler as LangfuseHandler

            handler = LangfuseHandler(
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                session_id=None,
                user_id=None,
            )
            callbacks.append(handler)
        except ImportError:
            pass

    return callbacks


class HealthcareCallbackHandler(BaseCallbackHandler):
    """
    Custom callback handler for healthcare-specific logging.
    Captures agent interactions, decisions, and rationale.
    """

    def __init__(self, session_id: str = None, user_id: str = None):
        super().__init__()
        self.session_id = session_id
        self.user_id = user_id
        self.traces = []

    def on_llm_start(self, serialized: dict, prompts: List[str], **kwargs) -> None:
        self.traces.append({
            "event": "llm_start",
            "model": serialized.get("name", "unknown"),
            "prompt_count": len(prompts),
            "session_id": self.session_id,
        })

    def on_llm_end(self, response, **kwargs) -> None:
        self.traces.append({
            "event": "llm_end",
            "generations": len(response.generations) if response.generations else 0,
            "session_id": self.session_id,
        })

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs) -> None:
        self.traces.append({
            "event": "chain_start",
            "chain": serialized.get("name", "unknown"),
            "input_keys": list(inputs.keys()) if isinstance(inputs, dict) else [],
            "session_id": self.session_id,
        })

    def on_chain_end(self, outputs: dict, **kwargs) -> None:
        self.traces.append({
            "event": "chain_end",
            "output_keys": list(outputs.keys()) if isinstance(outputs, dict) else [],
            "session_id": self.session_id,
        })

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        self.traces.append({
            "event": "tool_start",
            "tool": serialized.get("name", "unknown"),
            "session_id": self.session_id,
        })

    def on_tool_end(self, output: str, **kwargs) -> None:
        self.traces.append({
            "event": "tool_end",
            "output_length": len(output) if output else 0,
            "session_id": self.session_id,
        })

    def on_agent_action(self, action, **kwargs) -> None:
        self.traces.append({
            "event": "agent_action",
            "tool": action.tool if hasattr(action, "tool") else "unknown",
            "session_id": self.session_id,
        })

    def on_agent_finish(self, finish, **kwargs) -> None:
        self.traces.append({
            "event": "agent_finish",
            "session_id": self.session_id,
        })

    def get_traces(self) -> List[dict]:
        """Get all collected traces."""
        return self.traces

    def clear_traces(self) -> None:
        """Clear collected traces."""
        self.traces = []
