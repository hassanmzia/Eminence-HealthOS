"""
Observability Tracer for HealthOS Multi-Agent System

Provides unified tracing across LangSmith and Langfuse with
decision logging, agent conversation tracing, and span management.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps


class ObservabilityManager:
    """
    Unified observability manager for LangSmith and Langfuse.
    Provides tracing, logging, and explainability for agent decisions.
    """

    def __init__(self):
        self.langsmith_enabled = bool(os.environ.get("LANGCHAIN_API_KEY"))
        self.langfuse_enabled = bool(os.environ.get("LANGFUSE_PUBLIC_KEY"))

        if self.langsmith_enabled:
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            os.environ.setdefault("LANGCHAIN_PROJECT", "healthos-multi-agent")
            try:
                from langsmith import Client as LangSmithClient
                self.langsmith_client = LangSmithClient()
            except ImportError:
                self.langsmith_client = None
                self.langsmith_enabled = False
        else:
            self.langsmith_client = None

        if self.langfuse_enabled:
            try:
                from langfuse import Langfuse
                self.langfuse = Langfuse(
                    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                    host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                )
            except ImportError:
                self.langfuse = None
                self.langfuse_enabled = False
        else:
            self.langfuse = None

    def create_trace(
        self,
        name: str,
        session_id: str,
        user_id: str = None,
        metadata: Dict = None,
    ) -> "TraceContext":
        """Create a new trace for a query session."""
        return TraceContext(
            manager=self,
            name=name,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
        )

    def log_agent_decision(
        self,
        trace_id: str,
        agent_name: str,
        decision: str,
        rationale: str,
        input_data: Dict,
        output_data: Dict,
        confidence: float = None,
        alternatives: List[Dict] = None,
        duration_ms: int = 0,
    ):
        """Log an agent's decision with full explainability."""
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "agent": agent_name,
            "decision": decision,
            "rationale": rationale,
            "input": input_data,
            "output": output_data,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "duration_ms": duration_ms,
        }

        if self.langfuse:
            try:
                self.langfuse.score(
                    trace_id=trace_id,
                    name=f"{agent_name}_decision",
                    value=confidence or 0.8,
                    comment=rationale,
                )
            except Exception as e:
                print(f"Langfuse scoring failed: {e}")

        return decision_record

    def log_agent_conversation(
        self,
        trace_id: str,
        sender: str,
        receiver: str,
        message_type: str,
        content: Dict,
        response: Dict = None,
    ):
        """Log agent-to-agent communication."""
        conversation_record = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "sender": sender,
            "receiver": receiver,
            "message_type": message_type,
            "content": content,
            "response": response,
        }

        if self.langfuse:
            try:
                self.langfuse.generation(
                    trace_id=trace_id,
                    name=f"a2a_{sender}_to_{receiver}",
                    input=content,
                    output=response,
                    metadata={
                        "message_type": message_type,
                        "sender": sender,
                        "receiver": receiver,
                    },
                )
            except Exception as e:
                print(f"Langfuse generation logging failed: {e}")

        return conversation_record

    def flush(self):
        """Flush all pending traces."""
        if self.langfuse:
            self.langfuse.flush()


class TraceContext:
    """Context manager for a single trace/session."""

    def __init__(
        self,
        manager: ObservabilityManager,
        name: str,
        session_id: str,
        user_id: str = None,
        metadata: Dict = None,
    ):
        self.manager = manager
        self.name = name
        self.session_id = session_id
        self.user_id = user_id
        self.metadata = metadata or {}
        self.trace_id = str(uuid.uuid4())
        self.spans = []
        self.decisions = []
        self.conversations = []
        self.langfuse_trace = None
        self.start_time = None

    async def __aenter__(self):
        self.start_time = datetime.now()

        if self.manager.langfuse:
            try:
                self.langfuse_trace = self.manager.langfuse.trace(
                    id=self.trace_id,
                    name=self.name,
                    session_id=self.session_id,
                    user_id=self.user_id,
                    metadata=self.metadata,
                )
            except Exception as e:
                print(f"Failed to create Langfuse trace: {e}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.manager.flush()

    def span(self, name: str, input_data: Dict = None) -> "SpanContext":
        """Create a new span within this trace."""
        return SpanContext(trace=self, name=name, input_data=input_data)

    def log_decision(
        self,
        agent_name: str,
        decision: str,
        rationale: str,
        input_data: Dict,
        output_data: Dict,
        confidence: float = None,
        alternatives: List[Dict] = None,
        duration_ms: int = 0,
    ):
        """Log an agent decision within this trace."""
        record = self.manager.log_agent_decision(
            trace_id=self.trace_id,
            agent_name=agent_name,
            decision=decision,
            rationale=rationale,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            alternatives=alternatives,
            duration_ms=duration_ms,
        )
        self.decisions.append(record)
        return record

    def log_conversation(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        content: Dict,
        response: Dict = None,
    ):
        """Log agent-to-agent conversation within this trace."""
        record = self.manager.log_agent_conversation(
            trace_id=self.trace_id,
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content,
            response=response,
        )
        self.conversations.append(record)
        return record


class SpanContext:
    """Context manager for a span within a trace."""

    def __init__(self, trace: TraceContext, name: str, input_data: Dict = None):
        self.trace = trace
        self.name = name
        self.input_data = input_data or {}
        self.span_id = str(uuid.uuid4())
        self.start_time = None
        self.langfuse_span = None

    async def __aenter__(self):
        self.start_time = datetime.now()

        if self.trace.langfuse_trace and self.trace.manager.langfuse:
            try:
                self.langfuse_span = self.trace.langfuse_trace.span(
                    name=self.name, input=self.input_data
                )
            except Exception as e:
                print(f"Failed to create Langfuse span: {e}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.langfuse_span:
            try:
                self.langfuse_span.end()
            except Exception as e:
                print(f"Failed to end Langfuse span: {e}")

    def set_output(self, output: Dict):
        """Set the output for this span."""
        if self.langfuse_span:
            try:
                self.langfuse_span.update(output=output)
            except Exception as e:
                print(f"Failed to update Langfuse span: {e}")


def trace_agent_action(agent_name: str, action: str):
    """Decorator to trace agent actions."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, state, *args, **kwargs):
            start_time = datetime.now()
            obs_manager = getattr(self, "observability", None)

            try:
                result = await func(self, state, *args, **kwargs)
                duration_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )

                if obs_manager:
                    session_id = state.get("session_id", "unknown")
                    obs_manager.log_agent_conversation(
                        trace_id=session_id,
                        sender="orchestrator",
                        receiver=agent_name,
                        message_type="action",
                        content={"action": action, "input": _safe_serialize(state)},
                        response={
                            "output": _safe_serialize(result),
                            "duration_ms": duration_ms,
                        },
                    )

                return result

            except Exception as e:
                duration_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )

                if obs_manager:
                    session_id = state.get("session_id", "unknown")
                    obs_manager.log_agent_conversation(
                        trace_id=session_id,
                        sender="orchestrator",
                        receiver=agent_name,
                        message_type="error",
                        content={"action": action, "error": str(e)},
                        response={"duration_ms": duration_ms},
                    )
                raise

        return wrapper

    return decorator


def trace_decision(agent_name: str):
    """Decorator to trace agent decisions with rationale."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = datetime.now()
            result = await func(self, *args, **kwargs)
            duration_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            if isinstance(result, dict):
                obs_manager = getattr(self, "observability", None)
                if obs_manager:
                    obs_manager.log_agent_decision(
                        trace_id=result.get("session_id", "unknown"),
                        agent_name=agent_name,
                        decision=result.get("decision", "unknown"),
                        rationale=result.get("rationale", ""),
                        input_data=_safe_serialize(args),
                        output_data=_safe_serialize(result),
                        confidence=result.get("confidence"),
                        duration_ms=duration_ms,
                    )

            return result

        return wrapper

    return decorator


def _safe_serialize(obj) -> Dict:
    """Safely serialize an object for logging."""
    try:
        if isinstance(obj, dict):
            return {k: _truncate_value(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_truncate_value(v) for v in obj[:10]]
        else:
            return {"value": str(obj)[:500]}
    except Exception:
        return {"error": "serialization_failed"}


def _truncate_value(value, max_length: int = 200) -> Any:
    """Truncate values for logging."""
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."
    elif isinstance(value, (list, tuple)) and len(value) > 10:
        return list(value[:10]) + ["..."]
    elif isinstance(value, dict):
        return {k: _truncate_value(v, max_length) for k, v in list(value.items())[:10]}
    return value
