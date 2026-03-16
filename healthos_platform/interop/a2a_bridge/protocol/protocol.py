"""
A2A (Agent-to-Agent) Protocol

Redis-backed inter-agent communication with typed messages,
correlation IDs, TTLs, request/response patterns, and broadcast support.
"""

import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Literal, Callable, Awaitable
from dataclasses import dataclass, asdict
import redis.asyncio as redis


@dataclass
class A2AMessage:
    """A2A message format."""
    sender_agent: str
    receiver_agent: str
    message_type: Literal["request", "response", "notification", "error"]
    capability: str
    payload: Dict[str, Any]
    correlation_id: str
    timestamp: str
    priority: int = 5
    ttl_seconds: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        return cls(**data)

    @classmethod
    def create_request(
        cls,
        sender: str,
        receiver: str,
        capability: str,
        payload: Dict[str, Any],
        priority: int = 5,
    ) -> "A2AMessage":
        return cls(
            sender_agent=sender,
            receiver_agent=receiver,
            message_type="request",
            capability=capability,
            payload=payload,
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            priority=priority,
        )

    def create_response(self, payload: Dict[str, Any]) -> "A2AMessage":
        return A2AMessage(
            sender_agent=self.receiver_agent,
            receiver_agent=self.sender_agent,
            message_type="response",
            capability=self.capability,
            payload=payload,
            correlation_id=self.correlation_id,
            timestamp=datetime.now().isoformat(),
            priority=self.priority,
        )

    def create_error(self, error: str) -> "A2AMessage":
        return A2AMessage(
            sender_agent=self.receiver_agent,
            receiver_agent=self.sender_agent,
            message_type="error",
            capability=self.capability,
            payload={"error": error},
            correlation_id=self.correlation_id,
            timestamp=datetime.now().isoformat(),
            priority=self.priority,
        )


class A2AProtocol:
    """
    A2A Protocol implementation for agent communication.
    Uses Redis for message passing and pub/sub.
    """

    def __init__(self, agent_name: str, redis_client: redis.Redis):
        self.agent_name = agent_name
        self.redis = redis_client
        self.handlers: Dict[str, Callable[[A2AMessage], Awaitable[Dict[str, Any]]]] = {}

    async def send(self, message: A2AMessage) -> None:
        """Send a message to another agent."""
        queue_key = f"a2a:queue:{message.receiver_agent}"
        await self.redis.lpush(queue_key, json.dumps(message.to_dict()))
        await self.redis.expire(queue_key, message.ttl_seconds)
        await self.redis.publish(
            f"a2a:notify:{message.receiver_agent}", message.correlation_id
        )

    async def request(
        self,
        receiver: str,
        capability: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[A2AMessage]:
        """Send a request and wait for response."""
        message = A2AMessage.create_request(
            sender=self.agent_name,
            receiver=receiver,
            capability=capability,
            payload=payload,
        )
        await self.send(message)

        response_key = f"a2a:response:{message.correlation_id}"
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < timeout:
            response_data = await self.redis.get(response_key)
            if response_data:
                await self.redis.delete(response_key)
                return A2AMessage.from_dict(json.loads(response_data))
            await asyncio.sleep(0.1)

        return None

    async def receive(self) -> Optional[A2AMessage]:
        """Receive next message from queue."""
        queue_key = f"a2a:queue:{self.agent_name}"
        data = await self.redis.rpop(queue_key)
        if data:
            return A2AMessage.from_dict(json.loads(data))
        return None

    async def respond(self, original: A2AMessage, payload: Dict[str, Any]) -> None:
        """Send response to a request."""
        response = original.create_response(payload)
        response_key = f"a2a:response:{original.correlation_id}"
        await self.redis.setex(
            response_key,
            original.ttl_seconds,
            json.dumps(response.to_dict()),
        )

    def register_handler(
        self,
        capability: str,
        handler: Callable[[A2AMessage], Awaitable[Dict[str, Any]]],
    ) -> None:
        """Register a handler for a capability."""
        self.handlers[capability] = handler

    async def process_messages(self) -> None:
        """Process incoming messages."""
        while True:
            message = await self.receive()
            if not message:
                break

            if message.message_type == "request":
                handler = self.handlers.get(message.capability)
                if handler:
                    try:
                        result = await handler(message)
                        await self.respond(message, result)
                    except Exception as e:
                        error_response = message.create_error(str(e))
                        response_key = f"a2a:response:{message.correlation_id}"
                        await self.redis.setex(
                            response_key,
                            message.ttl_seconds,
                            json.dumps(error_response.to_dict()),
                        )

    async def broadcast(self, capability: str, payload: Dict[str, Any]) -> None:
        """Broadcast a notification to all agents."""
        message = A2AMessage(
            sender_agent=self.agent_name,
            receiver_agent="*",
            message_type="notification",
            capability=capability,
            payload=payload,
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
        )
        await self.redis.publish("a2a:broadcast", json.dumps(message.to_dict()))
