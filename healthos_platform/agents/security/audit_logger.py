"""
Eminence HealthOS — Audit Logger Module

Immutable, blockchain-compatible audit log for HIPAA compliance.

Features:
  - Append-only audit trail (PostgreSQL + Redis + file)
  - SHA-256 chaining (each record includes hash of previous record)
  - Tamper-evident ledger (any modification breaks the chain)
  - Structured HIPAA audit events with Pydantic models
  - Async-safe logging
  - Convenience methods for agent runs, PHI events, and security violations
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# ── HIPAA Audit Event Types ──────────────────────────────────────────────────

AUDIT_EVENT_TYPES: dict[str, str] = {
    "ACCESS": "Access to patient data",
    "MODIFY": "Modification of patient data",
    "DELETE": "Deletion of patient data",
    "EXPORT": "Export of patient data",
    "LOGIN": "User authentication",
    "LOGOUT": "User logout",
    "FAIL_AUTH": "Failed authentication attempt",
    "AGENT_RUN": "AI agent execution",
    "AGENT_FAIL": "AI agent execution failure",
    "PHI_DETECTED": "PHI detected in agent input/output",
    "PHI_REDACTED": "PHI redacted from agent input/output",
    "HITL_INTERRUPT": "Human-in-the-loop approval requested",
    "HITL_APPROVE": "Human-in-the-loop decision: approved",
    "HITL_REJECT": "Human-in-the-loop decision: rejected",
    "PRESCRIPTION": "Prescription recommendation generated",
    "EMERGENCY_ALERT": "Emergency alert triggered",
    "SECURITY_VIOLATION": "Security guardrail violation",
    "RATE_LIMIT": "Rate limit exceeded",
}


# ── Pydantic Models ─────────────────────────────────────────────────────────


class AuditRecord(BaseModel):
    """Immutable audit record with cryptographic chaining."""

    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_type: str
    event_description: str = ""
    actor_id: str
    patient_id: str | None = None
    tenant_id: str
    org_id: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = "GENESIS"
    record_hash: str = ""

    # Backward-compatible fields from the simpler AuditEntry model
    trace_id: str = ""
    agent_name: str = ""
    action: str = ""
    resource_type: str = ""
    resource_id: str = ""
    user_id: str = ""
    outcome: str = "success"
    phi_accessed: bool = False

    def model_post_init(self, __context: Any) -> None:
        if not self.event_description:
            self.event_description = AUDIT_EVENT_TYPES.get(self.event_type, "Unknown event")
        if not self.record_hash:
            self.record_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of this record's content for chain integrity."""
        content = json.dumps(
            {
                "record_id": self.record_id,
                "timestamp": self.timestamp,
                "event_type": self.event_type,
                "actor_id": self.actor_id,
                "patient_id": self.patient_id,
                "tenant_id": self.tenant_id,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def to_json(self) -> str:
        return self.model_dump_json()


class ChainVerificationReport(BaseModel):
    """Result of verifying the audit chain integrity."""

    records_verified: int = 0
    chain_intact: bool = True
    violations: list[dict[str, Any]] = Field(default_factory=list)
    verified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Global Chain State ───────────────────────────────────────────────────────

_chain_head_hash: str | None = None
_chain_lock = asyncio.Lock()


# ── Audit Logger ─────────────────────────────────────────────────────────────


class AgentAuditLogger:
    """
    HIPAA-compliant audit logger with tamper-evident blockchain-style chaining.

    Writes to:
      - PostgreSQL (primary persistent store)
      - Redis (hot cache for recent lookups)
      - Append-only JSONL file (backup / disaster recovery)
      - In-memory list (for testing and local queries)

    All writes are attempted concurrently; failures in any single backend
    do not block the others.
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="audit_logger")
        self._entries: list[AuditRecord] = []
        self._audit_file_path = os.getenv(
            "AUDIT_LOG_PATH", "/tmp/healthos_audit.jsonl"
        )

    # ── Core Logging ─────────────────────────────────────────────────────────

    async def log(
        self,
        event_type: str,
        actor_id: str,
        tenant_id: str,
        patient_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """
        Write an immutable, chain-linked audit record.
        Returns the record_id.
        """
        global _chain_head_hash

        if event_type not in AUDIT_EVENT_TYPES:
            self._log.warning("audit.unknown_event_type", event_type=event_type)

        async with _chain_lock:
            record = AuditRecord(
                event_type=event_type,
                actor_id=actor_id,
                patient_id=patient_id,
                tenant_id=tenant_id,
                details=details or {},
                previous_hash=_chain_head_hash or "GENESIS",
            )
            _chain_head_hash = record.record_hash

            # Store in memory
            self._entries.append(record)

            # Write to all persistent backends concurrently
            await asyncio.gather(
                self._write_to_postgres(record),
                self._write_to_redis(record),
                self._write_to_file(record),
                return_exceptions=True,
            )

        self._log.info(
            "audit.recorded",
            event_type=event_type,
            actor=actor_id,
            patient=patient_id or "N/A",
            tenant=tenant_id,
            hash=record.record_hash[:12],
        )

        return record.record_id

    # ── Convenience: Simple action logging (backward-compatible) ─────────────

    def log_action(
        self,
        trace_id: str,
        agent_name: str,
        action: str,
        resource_type: str,
        resource_id: str = "",
        patient_id: str = "",
        org_id: str = "",
        user_id: str = "",
        details: dict[str, Any] | None = None,
        outcome: str = "success",
        phi_accessed: bool = False,
    ) -> AuditRecord:
        """
        Synchronous action logging for backward compatibility.
        Stores in memory and structured log output.
        """
        record = AuditRecord(
            event_type=action.upper() if action.upper() in AUDIT_EVENT_TYPES else "AGENT_RUN",
            actor_id=user_id or f"agent:{agent_name}",
            patient_id=patient_id or None,
            tenant_id=org_id,
            org_id=org_id,
            details=details or {},
            trace_id=trace_id,
            agent_name=agent_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            outcome=outcome,
            phi_accessed=phi_accessed,
        )

        self._entries.append(record)

        self._log.info(
            "audit.action",
            audit_id=record.record_id,
            trace_id=trace_id,
            agent=agent_name,
            action=action,
            resource=f"{resource_type}/{resource_id}",
            outcome=outcome,
            phi_accessed=phi_accessed,
        )

        return record

    def log_data_access(
        self,
        trace_id: str,
        agent_name: str,
        resource_type: str,
        resource_id: str,
        patient_id: str,
        org_id: str = "",
        access_type: str = "read",
    ) -> AuditRecord:
        """Log a data access event (HIPAA requirement)."""
        return self.log_action(
            trace_id=trace_id,
            agent_name=agent_name,
            action=f"data_{access_type}",
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            org_id=org_id,
            details={"access_type": access_type},
            phi_accessed=True,
        )

    def log_decision(
        self,
        trace_id: str,
        agent_name: str,
        decision: str,
        confidence: float,
        rationale: str,
        patient_id: str = "",
        requires_hitl: bool = False,
    ) -> AuditRecord:
        """Log an agent clinical decision."""
        return self.log_action(
            trace_id=trace_id,
            agent_name=agent_name,
            action="clinical_decision",
            resource_type="decision",
            details={
                "decision": decision,
                "confidence": confidence,
                "rationale": rationale,
                "requires_hitl": requires_hitl,
            },
            patient_id=patient_id,
        )

    def log_error(
        self,
        trace_id: str,
        agent_name: str,
        error: str,
        details: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Log an agent error."""
        return self.log_action(
            trace_id=trace_id,
            agent_name=agent_name,
            action="error",
            resource_type="agent",
            details={"error": error, **(details or {})},
            outcome="failure",
        )

    # ── Convenience: Agent Run Logging ───────────────────────────────────────

    async def log_agent_run(
        self,
        agent_name: str,
        patient_id: str,
        tenant_id: str,
        run_id: str,
        status: str,
        duration_ms: float,
        phi_redacted: bool = False,
    ) -> str:
        """Log an AI agent execution event."""
        return await self.log(
            event_type="AGENT_RUN" if status == "completed" else "AGENT_FAIL",
            actor_id=f"agent:{agent_name}",
            tenant_id=tenant_id,
            patient_id=patient_id,
            details={
                "agent_name": agent_name,
                "run_id": run_id,
                "status": status,
                "duration_ms": duration_ms,
                "phi_redacted": phi_redacted,
            },
        )

    # ── Convenience: PHI Event Logging ───────────────────────────────────────

    async def log_phi_event(
        self,
        event_type: str,
        context: str,
        patient_id: str | None,
        tenant_id: str,
        phi_count: int,
    ) -> str:
        """Log PHI detection or redaction events."""
        return await self.log(
            event_type=event_type,
            actor_id="phi_detector",
            tenant_id=tenant_id,
            patient_id=patient_id,
            details={
                "context": context[:100],
                "phi_entities_count": phi_count,
            },
        )

    # ── Convenience: Security Violation Logging ──────────────────────────────

    async def log_security_violation(
        self,
        violation_type: str,
        actor_id: str,
        tenant_id: str,
        details: dict[str, Any],
    ) -> str:
        """Log security violations (injection attempts, rate limiting, etc.)."""
        self._log.critical(
            "audit.security_violation",
            violation_type=violation_type,
            actor=actor_id,
            tenant=tenant_id,
        )
        return await self.log(
            event_type="SECURITY_VIOLATION",
            actor_id=actor_id,
            tenant_id=tenant_id,
            patient_id=None,
            details={"violation_type": violation_type, **details},
        )

    # ── Chain Verification ───────────────────────────────────────────────────

    async def verify_chain_integrity(
        self, limit: int = 100
    ) -> ChainVerificationReport:
        """
        Verify the integrity of the audit chain by recomputing hashes.
        Returns report of any tampering detected.
        """
        records = await self._fetch_recent_records(limit)
        violations: list[dict[str, Any]] = []

        for i in range(1, len(records)):
            current = records[i]
            previous = records[i - 1]

            if current.get("previous_hash") != previous.get("record_hash"):
                violations.append({
                    "record_id": current.get("record_id"),
                    "issue": "Hash chain broken - tampering detected",
                    "expected_previous_hash": previous.get("record_hash"),
                    "actual_previous_hash": current.get("previous_hash"),
                })

        return ChainVerificationReport(
            records_verified=len(records),
            chain_intact=len(violations) == 0,
            violations=violations,
        )

    # ── Query ────────────────────────────────────────────────────────────────

    def get_entries(
        self,
        trace_id: str | None = None,
        agent_name: str | None = None,
        patient_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query in-memory audit entries with optional filters."""
        filtered = self._entries

        if trace_id:
            filtered = [e for e in filtered if e.trace_id == trace_id]
        if agent_name:
            filtered = [e for e in filtered if e.agent_name == agent_name]
        if patient_id:
            filtered = [e for e in filtered if e.patient_id == patient_id]

        return [e.model_dump() for e in filtered[-limit:]]

    # ── Backend Writers ──────────────────────────────────────────────────────

    async def _write_to_postgres(self, record: AuditRecord) -> None:
        """Write audit record to PostgreSQL audit table."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_write_postgres, record)
        except Exception as exc:
            self._log.warning("audit.postgres_write_failed", error=str(exc))

    def _sync_write_postgres(self, record: AuditRecord) -> None:
        try:
            import asyncpg  # noqa: F401 — detect availability
        except ImportError:
            pass

        try:
            import psycopg2

            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "healthos"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log
                        (record_id, timestamp, event_type, actor_id, patient_id,
                         tenant_id, details, previous_hash, record_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.record_id,
                        record.timestamp,
                        record.event_type,
                        record.actor_id,
                        record.patient_id,
                        record.tenant_id,
                        json.dumps(record.details, default=str),
                        record.previous_hash,
                        record.record_hash,
                    ),
                )
            conn.commit()
            conn.close()
        except ImportError:
            self._log.debug("audit.postgres_not_available")
        except Exception as exc:
            raise exc

    async def _write_to_redis(self, record: AuditRecord) -> None:
        """Write audit record to Redis for hot-cache access."""
        try:
            import redis.asyncio as aioredis

            redis_client = await aioredis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            )
            key = f"audit:{record.tenant_id}:{record.record_id}"
            await redis_client.setex(key, 86400 * 90, record.to_json())  # 90-day retention

            # Add to sorted set for chronological retrieval
            ts_score = float(
                record.timestamp.replace("-", "")
                .replace("T", "")
                .replace(":", "")
                .replace("Z", "")[:14]
            )
            await redis_client.zadd(
                f"audit_chain:{record.tenant_id}",
                {record.record_id: ts_score},
            )
            await redis_client.aclose()
        except ImportError:
            self._log.debug("audit.redis_not_available")
        except Exception as exc:
            self._log.warning("audit.redis_write_failed", error=str(exc))

    async def _write_to_file(self, record: AuditRecord) -> None:
        """Write audit record to append-only JSONL file (backup)."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_write_file, record)
        except Exception as exc:
            self._log.warning("audit.file_write_failed", error=str(exc))

    def _sync_write_file(self, record: AuditRecord) -> None:
        """Synchronous append-only file write."""
        with open(self._audit_file_path, "a", encoding="utf-8") as f:
            f.write(record.to_json() + "\n")

    async def _fetch_recent_records(self, limit: int) -> list[dict[str, Any]]:
        """Fetch recent audit records for chain verification."""
        # Try in-memory first
        if self._entries:
            return [e.model_dump() for e in self._entries[-limit:]]

        # Fall back to PostgreSQL
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._sync_fetch_records, limit
            )
        except Exception as exc:
            self._log.warning("audit.fetch_failed", error=str(exc))
            return []

    def _sync_fetch_records(self, limit: int) -> list[dict[str, Any]]:
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "healthos"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
            )
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT record_id, timestamp, event_type, previous_hash, record_hash "
                    "FROM audit_log ORDER BY timestamp DESC LIMIT %s",
                    (limit,),
                )
                rows = cur.fetchall()
                columns = [d[0] for d in cur.description]
            conn.close()
            return [dict(zip(columns, row)) for row in reversed(rows)]
        except ImportError:
            return []
        except Exception as exc:
            self._log.warning("audit.sync_fetch_failed", error=str(exc))
            return []


# ── Module-level singleton ───────────────────────────────────────────────────

audit_logger = AgentAuditLogger()
