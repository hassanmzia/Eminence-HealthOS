"""
HealthOS Agent Observability Module

Unified tracing across LangSmith and Langfuse for multi-agent workflows.
Provides decision logging, agent conversation tracing, and span management.
"""

from .tracer import ObservabilityManager, TraceContext, trace_agent_action, trace_decision
from .callbacks import HealthcareCallbackHandler, get_langsmith_callbacks, get_langfuse_callbacks

__all__ = [
    "ObservabilityManager",
    "TraceContext",
    "trace_agent_action",
    "trace_decision",
    "HealthcareCallbackHandler",
    "get_langsmith_callbacks",
    "get_langfuse_callbacks",
]
