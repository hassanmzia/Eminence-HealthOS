"""Base agent interface and registry for the multi-agent system."""
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger('agents')


@dataclass
class AgentOutput:
    """Standardized output from any agent."""
    agent: str
    patient_id: str
    payload: Dict[str, Any]
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class BaseAgent(ABC):
    """Abstract base for all agents in the MS Risk Lab system."""

    name: str = "base"

    @abstractmethod
    def execute(self, *args, **kwargs) -> AgentOutput:
        pass

    def timed_execute(self, *args, **kwargs) -> AgentOutput:
        start = time.time()
        result = self.execute(*args, **kwargs)
        result.duration_ms = (time.time() - start) * 1000
        logger.info(f"Agent {self.name} completed in {result.duration_ms:.1f}ms")
        return result


class AgentRegistry:
    """Registry for discovering and managing agents."""
    _agents: Dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent: BaseAgent):
        cls._agents[agent.name] = agent
        return agent

    @classmethod
    def get(cls, name: str) -> Optional[BaseAgent]:
        return cls._agents.get(name)

    @classmethod
    def all(cls) -> Dict[str, BaseAgent]:
        return cls._agents.copy()
