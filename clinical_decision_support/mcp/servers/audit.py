"""
HIPAA-Compliant Audit Logging for Healthcare MCP Servers
Persists audit logs to PostgreSQL for compliance and security.
"""

import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

# Database configuration
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("AUDIT_DB_NAME", "healthapp")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class AuditEventType(str, Enum):
    """Types of audit events"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # Data access events
    PATIENT_VIEW = "patient_view"
    PATIENT_SEARCH = "patient_search"
    PHI_ACCESS = "phi_access"
    RECORD_VIEW = "record_view"

    # Data modification events
    RECORD_CREATE = "record_create"
    RECORD_UPDATE = "record_update"
    RECORD_DELETE = "record_delete"

    # Clinical events
    ORDER_PLACED = "order_placed"
    PRESCRIPTION_CREATED = "prescription_created"
    DIAGNOSIS_RECORDED = "diagnosis_recorded"
    ASSESSMENT_RUN = "assessment_run"

    # MCP tool invocations
    MCP_TOOL_CALL = "mcp_tool_call"
    MCP_TOOL_SUCCESS = "mcp_tool_success"
    MCP_TOOL_ERROR = "mcp_tool_error"

    # LLM events
    LLM_QUERY = "llm_query"
    LLM_RESPONSE = "llm_response"

    # Security events
    PERMISSION_DENIED = "permission_denied"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGE = "configuration_change"


class AuditSeverity(str, Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """HIPAA-compliant audit log entry"""
    # Required fields
    event_type: AuditEventType
    timestamp: datetime
    user_id: str
    action: str

    # Optional fields
    patient_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None

    # Event details
    success: bool = True
    severity: AuditSeverity = AuditSeverity.INFO
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    # Network information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # PHI access tracking
    phi_accessed: bool = False
    phi_fields: Optional[List[str]] = None

    # Error information
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        if self.details:
            data["details"] = json.dumps(self.details)
        if self.phi_fields:
            data["phi_fields"] = json.dumps(self.phi_fields)
        return data


class AuditLogger:
    """
    HIPAA-compliant audit logger with PostgreSQL persistence.
    Implements the security audit requirements for healthcare applications.
    """

    def __init__(self):
        self._pool = None
        self._initialized = False
        self._buffer: List[AuditEntry] = []
        self._buffer_size = int(os.getenv("AUDIT_BUFFER_SIZE", "10"))
        self._flush_interval = int(os.getenv("AUDIT_FLUSH_INTERVAL", "5"))

    async def initialize(self):
        """Initialize database connection pool and create tables"""
        if self._initialized:
            return

        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10
            )

            # Create audit tables
            await self._create_tables()
            self._initialized = True

            # Start background flush task
            asyncio.create_task(self._periodic_flush())

            logger.info("Audit logger initialized successfully")

        except ImportError:
            logger.warning("asyncpg not installed, using console logging only")
        except Exception as e:
            logger.error(f"Failed to initialize audit logger: {e}")

    async def _create_tables(self):
        """Create audit log tables if they don't exist"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            user_id VARCHAR(100) NOT NULL,
            action VARCHAR(255) NOT NULL,

            patient_id VARCHAR(100),
            resource_type VARCHAR(100),
            resource_id VARCHAR(100),
            request_id VARCHAR(100),
            session_id VARCHAR(100),

            success BOOLEAN DEFAULT TRUE,
            severity VARCHAR(20) DEFAULT 'info',
            description TEXT,
            details JSONB,

            ip_address INET,
            user_agent TEXT,

            phi_accessed BOOLEAN DEFAULT FALSE,
            phi_fields JSONB,

            error_message TEXT,
            error_code VARCHAR(50),

            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_patient_id ON audit_logs(patient_id);
        CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
        CREATE INDEX IF NOT EXISTS idx_audit_phi_accessed ON audit_logs(phi_accessed) WHERE phi_accessed = TRUE;

        -- Partition table by month for performance (optional, commented out for simplicity)
        -- CREATE TABLE IF NOT EXISTS audit_logs_partition OF audit_logs
        --     FOR VALUES FROM (MINVALUE) TO (MAXVALUE)
        --     PARTITION BY RANGE (timestamp);
        """

        async with self._pool.acquire() as conn:
            await conn.execute(create_sql)

    async def log(self, entry: AuditEntry):
        """Log an audit entry"""
        # Add to buffer
        self._buffer.append(entry)

        # Console log for immediate visibility
        log_level = logging.INFO
        if entry.severity == AuditSeverity.WARNING:
            log_level = logging.WARNING
        elif entry.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            log_level = logging.ERROR

        logger.log(log_level, f"AUDIT: {entry.event_type.value} - {entry.action} - user:{entry.user_id} patient:{entry.patient_id}")

        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            await self.flush()

    async def flush(self):
        """Flush buffered entries to database"""
        if not self._buffer:
            return

        if not self._pool:
            # Not connected to database, just clear buffer
            self._buffer.clear()
            return

        entries_to_flush = self._buffer.copy()
        self._buffer.clear()

        try:
            async with self._pool.acquire() as conn:
                # Batch insert
                await conn.executemany(
                    """
                    INSERT INTO audit_logs (
                        event_type, timestamp, user_id, action,
                        patient_id, resource_type, resource_id, request_id, session_id,
                        success, severity, description, details,
                        ip_address, user_agent,
                        phi_accessed, phi_fields,
                        error_message, error_code
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9,
                        $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
                    )
                    """,
                    [
                        (
                            e.event_type.value,
                            e.timestamp,
                            e.user_id,
                            e.action,
                            e.patient_id,
                            e.resource_type,
                            e.resource_id,
                            e.request_id,
                            e.session_id,
                            e.success,
                            e.severity.value,
                            e.description,
                            json.dumps(e.details) if e.details else None,
                            e.ip_address,
                            e.user_agent,
                            e.phi_accessed,
                            json.dumps(e.phi_fields) if e.phi_fields else None,
                            e.error_message,
                            e.error_code
                        )
                        for e in entries_to_flush
                    ]
                )

        except Exception as e:
            logger.error(f"Failed to flush audit logs: {e}")
            # Re-add entries to buffer for retry
            self._buffer.extend(entries_to_flush)

    async def _periodic_flush(self):
        """Periodically flush buffer to database"""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self.flush()

    async def query(
        self,
        user_id: str = None,
        patient_id: str = None,
        event_type: AuditEventType = None,
        start_date: datetime = None,
        end_date: datetime = None,
        phi_only: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit logs"""
        if not self._pool:
            return []

        conditions = []
        params = []
        param_idx = 1

        if user_id:
            conditions.append(f"user_id = ${param_idx}")
            params.append(user_id)
            param_idx += 1

        if patient_id:
            conditions.append(f"patient_id = ${param_idx}")
            params.append(patient_id)
            param_idx += 1

        if event_type:
            conditions.append(f"event_type = ${param_idx}")
            params.append(event_type.value)
            param_idx += 1

        if start_date:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(start_date)
            param_idx += 1

        if end_date:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(end_date)
            param_idx += 1

        if phi_only:
            conditions.append("phi_accessed = TRUE")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM audit_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_idx}
        """
        params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def get_patient_access_report(self, patient_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate patient access report for HIPAA compliance"""
        if not self._pool:
            return {"error": "Database not available"}

        async with self._pool.acquire() as conn:
            # Get all access events for patient
            access_events = await conn.fetch(
                """
                SELECT user_id, event_type, action, timestamp, phi_accessed, phi_fields
                FROM audit_logs
                WHERE patient_id = $1
                AND timestamp >= NOW() - INTERVAL '%s days'
                ORDER BY timestamp DESC
                """,
                patient_id, days
            )

            # Get unique users who accessed
            unique_users = await conn.fetch(
                """
                SELECT DISTINCT user_id, COUNT(*) as access_count
                FROM audit_logs
                WHERE patient_id = $1
                AND timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY user_id
                """,
                patient_id, days
            )

            # Get PHI access breakdown
            phi_access = await conn.fetch(
                """
                SELECT phi_fields, COUNT(*) as count
                FROM audit_logs
                WHERE patient_id = $1
                AND phi_accessed = TRUE
                AND timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY phi_fields
                """,
                patient_id, days
            )

            return {
                "patient_id": patient_id,
                "report_period_days": days,
                "total_access_events": len(access_events),
                "unique_users": len(unique_users),
                "users": [{"user_id": r["user_id"], "access_count": r["access_count"]} for r in unique_users],
                "phi_access_breakdown": [dict(r) for r in phi_access],
                "recent_events": [dict(r) for r in access_events[:50]]
            }

    async def close(self):
        """Close database connection"""
        if self._pool:
            await self.flush()
            await self._pool.close()


# Singleton instance
audit_logger = AuditLogger()


# Convenience functions
async def log_mcp_tool_call(
    tool_name: str,
    user_id: str,
    patient_id: str = None,
    request_id: str = None,
    arguments: dict = None,
    ip_address: str = None
):
    """Log MCP tool invocation"""
    await audit_logger.log(AuditEntry(
        event_type=AuditEventType.MCP_TOOL_CALL,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action=f"tool:{tool_name}",
        patient_id=patient_id,
        request_id=request_id,
        resource_type="mcp_tool",
        resource_id=tool_name,
        phi_accessed=patient_id is not None,
        details={"arguments": arguments} if arguments else None,
        ip_address=ip_address
    ))


async def log_phi_access(
    user_id: str,
    patient_id: str,
    resource_type: str,
    fields_accessed: List[str],
    action: str = "view",
    ip_address: str = None
):
    """Log PHI (Protected Health Information) access"""
    await audit_logger.log(AuditEntry(
        event_type=AuditEventType.PHI_ACCESS,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action=f"phi_access:{action}",
        patient_id=patient_id,
        resource_type=resource_type,
        phi_accessed=True,
        phi_fields=fields_accessed,
        ip_address=ip_address
    ))


async def log_clinical_assessment(
    user_id: str,
    patient_id: str,
    assessment_type: str,
    findings: dict = None,
    success: bool = True,
    error: str = None
):
    """Log clinical assessment execution"""
    await audit_logger.log(AuditEntry(
        event_type=AuditEventType.ASSESSMENT_RUN,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action=f"assessment:{assessment_type}",
        patient_id=patient_id,
        resource_type="clinical_assessment",
        success=success,
        phi_accessed=True,
        details=findings,
        error_message=error,
        severity=AuditSeverity.ERROR if error else AuditSeverity.INFO
    ))


async def log_security_event(
    event_type: AuditEventType,
    user_id: str,
    action: str,
    description: str,
    ip_address: str = None,
    severity: AuditSeverity = AuditSeverity.WARNING
):
    """Log security-related event"""
    await audit_logger.log(AuditEntry(
        event_type=event_type,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action=action,
        description=description,
        severity=severity,
        ip_address=ip_address
    ))
