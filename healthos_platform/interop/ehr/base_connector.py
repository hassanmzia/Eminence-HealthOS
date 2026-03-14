"""
Eminence HealthOS — Abstract EHR Connector

Defines the contract that all EHR connectors (FHIR, HL7v2, proprietary) must
implement, along with shared retry and audit-logging decorators.
"""

from __future__ import annotations

import asyncio
import functools
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Retry decorator for transient EHR connectivity failures
# ---------------------------------------------------------------------------

def ehr_retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    ),
) -> Callable[[F], F]:
    """
    Async retry decorator with exponential backoff.

    Retries the wrapped coroutine on transient network/connection errors,
    logging each retry attempt for operational visibility.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        delay = backoff_base * (2 ** (attempt - 1))
                        logger.warning(
                            "ehr.retry",
                            function=fn.__qualname__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            delay_seconds=delay,
                            error=str(exc),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "ehr.retry_exhausted",
                            function=fn.__qualname__,
                            attempts=max_attempts,
                            error=str(exc),
                        )
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Audit-logging decorator for all sync operations
# ---------------------------------------------------------------------------

def audit_sync(operation: str) -> Callable[[F], F]:
    """
    Decorator that logs the start, success, and failure of every sync
    operation with timing, connector name, and operation metadata.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(self: BaseEHRConnector, *args: Any, **kwargs: Any) -> Any:
            trace_id = str(uuid.uuid4())
            start = time.monotonic()

            logger.info(
                "ehr.sync.start",
                trace_id=trace_id,
                connector=self.connector_name,
                operation=operation,
                function=fn.__qualname__,
            )

            try:
                result = await fn(self, *args, **kwargs)
                elapsed_ms = round((time.monotonic() - start) * 1000, 2)
                logger.info(
                    "ehr.sync.success",
                    trace_id=trace_id,
                    connector=self.connector_name,
                    operation=operation,
                    duration_ms=elapsed_ms,
                )
                # Store audit entry for later retrieval
                self._audit_log.append({
                    "trace_id": trace_id,
                    "connector": self.connector_name,
                    "operation": operation,
                    "status": "success",
                    "duration_ms": elapsed_ms,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                return result

            except Exception as exc:
                elapsed_ms = round((time.monotonic() - start) * 1000, 2)
                logger.error(
                    "ehr.sync.failure",
                    trace_id=trace_id,
                    connector=self.connector_name,
                    operation=operation,
                    duration_ms=elapsed_ms,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                self._audit_log.append({
                    "trace_id": trace_id,
                    "connector": self.connector_name,
                    "operation": operation,
                    "status": "failure",
                    "duration_ms": elapsed_ms,
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Abstract base connector
# ---------------------------------------------------------------------------

class BaseEHRConnector(ABC):
    """
    Abstract base class for EHR connectors.

    Every concrete connector (FHIR R4, HL7v2, proprietary vendor APIs) must
    implement these methods to participate in the EHR sync framework.
    """

    def __init__(self, connector_name: str = "unknown") -> None:
        self.connector_name = connector_name
        self._audit_log: list[dict[str, Any]] = []

    # -- Connection lifecycle ------------------------------------------------

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the remote EHR system."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection."""
        ...

    @abstractmethod
    async def is_connected(self) -> bool:
        """Return True if the connector currently has an active connection."""
        ...

    # -- Encounter sync ------------------------------------------------------

    @abstractmethod
    async def sync_encounter(self, encounter: Any) -> dict:
        """
        Push an internal Encounter to the remote EHR.

        Returns a FHIR Bundle dict (for FHIR connectors) or an
        acknowledgement dict (for HL7v2 connectors).
        """
        ...

    @abstractmethod
    async def fetch_encounters(
        self,
        patient_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> list[dict]:
        """
        Fetch encounters for a patient from the remote EHR.

        Args:
            patient_id: The patient identifier on the remote system.
            date_range: Optional (start, end) datetime window.

        Returns:
            A list of encounter dicts in internal or FHIR format.
        """
        ...

    # -- Patient sync --------------------------------------------------------

    @abstractmethod
    async def sync_patient(self, patient: Any) -> dict:
        """
        Push an internal Patient record to the remote EHR.

        Returns a FHIR Patient dict or acknowledgement.
        """
        ...

    @abstractmethod
    async def fetch_patient(self, patient_id: str) -> dict:
        """
        Fetch a single patient record from the remote EHR.

        Returns patient data as a dict.
        """
        ...

    # -- Clinical data push --------------------------------------------------

    @abstractmethod
    async def push_clinical_note(self, note: Any) -> str:
        """
        Push a clinical note (SOAP, progress, procedure) to the remote EHR.

        Returns the remote resource ID assigned by the EHR.
        """
        ...

    @abstractmethod
    async def push_observation(self, observation: Any) -> str:
        """
        Push a vital-sign observation to the remote EHR.

        Returns the remote resource ID assigned by the EHR.
        """
        ...

    # -- Audit convenience ---------------------------------------------------

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return a copy of the in-memory audit log for this connector."""
        return list(self._audit_log)

    def clear_audit_log(self) -> None:
        """Clear the in-memory audit log."""
        self._audit_log.clear()
