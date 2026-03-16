"""
HITL Agent

Manages human-in-the-loop approval workflows.
Uses Redis for task persistence (24h TTL) and pub/sub for real-time notifications.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis.asyncio as redis


class HITLAgent:
    """Agent for managing HITL approval workflows."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.approval_expiry = timedelta(hours=24)

    async def create_approval_request(
        self,
        session_id: str,
        query: str,
        sql: str,
        query_type: str,
        risk_score: float,
        risk_assessment: str,
    ) -> str:
        """Create a new approval request. Returns task_id."""
        task_id = str(uuid.uuid4())

        request = {
            "task_id": task_id,
            "session_id": session_id,
            "natural_language_query": query,
            "generated_sql": sql,
            "query_type": query_type,
            "risk_score": risk_score,
            "risk_assessment": risk_assessment,
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + self.approval_expiry).isoformat(),
        }

        await self.redis.setex(
            f"hitl:task:{task_id}",
            int(self.approval_expiry.total_seconds()),
            json.dumps(request),
        )

        await self.redis.lpush("hitl:pending", task_id)

        await self.redis.publish(
            "hitl:new_task",
            json.dumps({
                "task_id": task_id,
                "session_id": session_id,
                "query_type": query_type,
                "risk_score": risk_score,
            }),
        )

        return task_id

    async def get_approval_request(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get an approval request by ID."""
        data = await self.redis.get(f"hitl:task:{task_id}")
        if data:
            return json.loads(data)
        return None

    async def get_pending_requests(self) -> list:
        """Get all pending approval requests."""
        task_ids = await self.redis.lrange("hitl:pending", 0, -1)
        requests = []

        for task_id in task_ids:
            request = await self.get_approval_request(task_id.decode())
            if request and request.get("status") == "PENDING":
                requests.append(request)

        return requests

    async def process_decision(
        self,
        task_id: str,
        decision: str,
        reviewer_id: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Process a human decision on a pending task."""
        request = await self.get_approval_request(task_id)
        if not request:
            raise ValueError(f"Task not found: {task_id}")

        if request["status"] != "PENDING":
            raise ValueError(f"Task is not pending: {request['status']}")

        request["status"] = decision.upper()
        request["reviewer_id"] = reviewer_id
        request["review_notes"] = notes
        request["reviewed_at"] = datetime.now().isoformat()

        await self.redis.set(
            f"hitl:task:{task_id}",
            json.dumps(request),
        )

        await self.redis.lrem("hitl:pending", 0, task_id)

        await self.redis.publish(
            "hitl:decision",
            json.dumps({
                "task_id": task_id,
                "session_id": request["session_id"],
                "decision": decision,
                "reviewer_id": reviewer_id,
            }),
        )

        return request

    async def escalate(
        self, task_id: str, target: str, reason: str
    ) -> Dict[str, Any]:
        """Escalate an approval request to a higher authority."""
        request = await self.get_approval_request(task_id)
        if not request:
            raise ValueError(f"Task not found: {task_id}")

        request["status"] = "ESCALATED"
        request["escalation_target"] = target
        request["escalation_reason"] = reason
        request["escalated_at"] = datetime.now().isoformat()

        await self.redis.set(
            f"hitl:task:{task_id}",
            json.dumps(request),
        )

        await self.redis.publish(
            "hitl:escalation",
            json.dumps({
                "task_id": task_id,
                "target": target,
                "reason": reason,
            }),
        )

        return request
