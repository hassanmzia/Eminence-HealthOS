"""
Eminence HealthOS — Payer System Integration Connectors
Provides a unified interface for communicating with insurance payers via
X12 EDI transactions (270/271, 278, 837), REST APIs, and FHIR-based
payer endpoints. Connector implementations are pluggable per payer.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("healthos.payer.connector")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class TransactionType(str, Enum):
    ELIGIBILITY_INQUIRY = "270"       # Eligibility, Coverage, or Benefit Inquiry
    ELIGIBILITY_RESPONSE = "271"      # Eligibility, Coverage, or Benefit Response
    PRIOR_AUTH_REQUEST = "278_REQ"     # Health Care Services Review Request
    PRIOR_AUTH_RESPONSE = "278_RESP"   # Health Care Services Review Response
    CLAIM_SUBMISSION = "837P"         # Professional Claim
    CLAIM_STATUS_INQ = "276"          # Claim Status Request
    CLAIM_STATUS_RESP = "277"         # Claim Status Response
    REMITTANCE_ADVICE = "835"         # Payment/Remittance Advice


class PayerTransaction(BaseModel):
    """Represents a single transaction with a payer."""

    transaction_id: str = Field(default_factory=lambda: f"TXN-{uuid.uuid4().hex[:12]}")
    payer_id: str
    transaction_type: TransactionType
    direction: str = "outbound"  # outbound (to payer) or inbound (from payer)
    request_data: dict[str, Any] = Field(default_factory=dict)
    response_data: dict[str, Any] | None = None
    status: str = "pending"  # pending, sent, acknowledged, completed, error
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class EligibilityRequest(BaseModel):
    """Standardized eligibility inquiry."""

    member_id: str
    group_number: str = ""
    subscriber_dob: str = ""
    subscriber_name: str = ""
    provider_npi: str = ""
    date_of_service: str = ""
    service_type: str = "30"  # health benefit plan coverage


class EligibilityResponse(BaseModel):
    """Standardized eligibility response."""

    eligible: bool
    plan_name: str = ""
    plan_type: str = ""
    coverage_status: str = ""
    effective_date: str = ""
    termination_date: str | None = None
    copay: dict[str, float] = Field(default_factory=dict)
    deductible: dict[str, float] = Field(default_factory=dict)
    coinsurance: dict[str, float] = Field(default_factory=dict)
    out_of_pocket_max: dict[str, float] = Field(default_factory=dict)
    prior_auth_required: bool = False
    raw_response: dict[str, Any] = Field(default_factory=dict)


class ClaimSubmission(BaseModel):
    """Standardized claim submission."""

    claim_id: str
    patient_member_id: str
    provider_npi: str
    date_of_service: str
    place_of_service: str = "11"  # office
    diagnosis_codes: list[str] = Field(default_factory=list)
    service_lines: list[dict[str, Any]] = Field(default_factory=list)
    total_charges: float = 0
    prior_auth_reference: str | None = None


class ClaimResponse(BaseModel):
    """Standardized claim response."""

    claim_id: str
    payer_claim_number: str = ""
    status: str = ""  # accepted, rejected, denied, pended, paid
    allowed_amount: float | None = None
    paid_amount: float | None = None
    patient_responsibility: float | None = None
    denial_reason: str | None = None
    adjustment_codes: list[dict[str, Any]] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# ABSTRACT CONNECTOR
# ═══════════════════════════════════════════════════════════════════════════════


class BasePayerConnector(ABC):
    """Abstract base class for payer system connectors."""

    payer_id: str = ""
    payer_name: str = ""
    supports_real_time: bool = False

    @abstractmethod
    async def check_eligibility(self, request: EligibilityRequest) -> EligibilityResponse:
        """Submit an eligibility inquiry (X12 270) and return response (271)."""
        ...

    @abstractmethod
    async def submit_prior_auth(self, request: dict[str, Any]) -> dict[str, Any]:
        """Submit a prior authorization request (X12 278)."""
        ...

    @abstractmethod
    async def submit_claim(self, claim: ClaimSubmission) -> ClaimResponse:
        """Submit a claim (X12 837P) and return acknowledgment."""
        ...

    @abstractmethod
    async def check_claim_status(self, claim_id: str) -> dict[str, Any]:
        """Check claim status (X12 276/277)."""
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# PAYER CONNECTORS
# ═══════════════════════════════════════════════════════════════════════════════


class GenericPayerConnector(BasePayerConnector):
    """
    Generic payer connector that simulates X12 EDI transactions.
    In production, this would be replaced with real clearinghouse
    integrations (e.g., Availity, Change Healthcare, Trizetto).
    """

    def __init__(self, payer_id: str, payer_name: str) -> None:
        self.payer_id = payer_id
        self.payer_name = payer_name
        self.supports_real_time = True
        self._transactions: list[PayerTransaction] = []

    async def check_eligibility(self, request: EligibilityRequest) -> EligibilityResponse:
        txn = PayerTransaction(
            payer_id=self.payer_id,
            transaction_type=TransactionType.ELIGIBILITY_INQUIRY,
            request_data=request.model_dump(),
        )

        # Simulate eligibility check
        response = EligibilityResponse(
            eligible=True,
            plan_name=f"{self.payer_name} Standard PPO",
            plan_type="PPO",
            coverage_status="active",
            effective_date="2025-01-01",
            copay={"primary_care": 30, "specialist": 50, "emergency": 250},
            deductible={"individual": 1500, "individual_remaining": 750, "family": 3000},
            coinsurance={"in_network": 20, "out_of_network": 40},
            out_of_pocket_max={"individual": 6500, "individual_remaining": 4500, "family": 13000},
            prior_auth_required=False,
        )

        txn.response_data = response.model_dump()
        txn.status = "completed"
        txn.completed_at = datetime.now(timezone.utc)
        self._transactions.append(txn)

        logger.info("payer.eligibility.checked", extra={
            "payer": self.payer_id, "member": request.member_id, "eligible": True,
        })

        return response

    async def submit_prior_auth(self, request: dict[str, Any]) -> dict[str, Any]:
        txn = PayerTransaction(
            payer_id=self.payer_id,
            transaction_type=TransactionType.PRIOR_AUTH_REQUEST,
            request_data=request,
        )

        auth_number = f"AUTH-{self.payer_id[:3].upper()}-{uuid.uuid4().hex[:8]}"

        response = {
            "auth_number": auth_number,
            "status": "pended",  # pending payer review
            "estimated_response_hours": 48,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        txn.response_data = response
        txn.status = "completed"
        txn.completed_at = datetime.now(timezone.utc)
        self._transactions.append(txn)

        return response

    async def submit_claim(self, claim: ClaimSubmission) -> ClaimResponse:
        txn = PayerTransaction(
            payer_id=self.payer_id,
            transaction_type=TransactionType.CLAIM_SUBMISSION,
            request_data=claim.model_dump(),
        )

        payer_claim_number = f"PCN-{uuid.uuid4().hex[:10].upper()}"

        response = ClaimResponse(
            claim_id=claim.claim_id,
            payer_claim_number=payer_claim_number,
            status="accepted",
            allowed_amount=claim.total_charges * 0.85,
            paid_amount=claim.total_charges * 0.65,
            patient_responsibility=claim.total_charges * 0.20,
        )

        txn.response_data = response.model_dump()
        txn.status = "completed"
        txn.completed_at = datetime.now(timezone.utc)
        self._transactions.append(txn)

        logger.info("payer.claim.submitted", extra={
            "payer": self.payer_id, "claim": claim.claim_id, "status": "accepted",
        })

        return response

    async def check_claim_status(self, claim_id: str) -> dict[str, Any]:
        txn = PayerTransaction(
            payer_id=self.payer_id,
            transaction_type=TransactionType.CLAIM_STATUS_INQ,
            request_data={"claim_id": claim_id},
        )

        response = {
            "claim_id": claim_id,
            "status": "in_process",
            "status_category": "A2",  # accepted
            "status_code": "WC",  # waiting for coverage
            "effective_date": datetime.now(timezone.utc).isoformat(),
        }

        txn.response_data = response
        txn.status = "completed"
        txn.completed_at = datetime.now(timezone.utc)
        self._transactions.append(txn)

        return response

    @property
    def transaction_log(self) -> list[dict[str, Any]]:
        return [
            {
                "transaction_id": t.transaction_id,
                "type": t.transaction_type.value,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in self._transactions
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTOR REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class PayerConnectorRegistry:
    """Registry for managing payer connectors."""

    def __init__(self) -> None:
        self._connectors: dict[str, BasePayerConnector] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default payer connectors."""
        defaults = [
            ("aetna", "Aetna"),
            ("unitedhealth", "UnitedHealthcare"),
            ("cigna", "Cigna"),
            ("anthem", "Anthem BCBS"),
            ("humana", "Humana"),
            ("medicare", "CMS Medicare"),
            ("medicaid", "State Medicaid"),
        ]
        for payer_id, name in defaults:
            self._connectors[payer_id] = GenericPayerConnector(payer_id, name)

    def get(self, payer_id: str) -> BasePayerConnector | None:
        """Get a connector by payer ID."""
        return self._connectors.get(payer_id.lower())

    def register(self, connector: BasePayerConnector) -> None:
        """Register a custom payer connector."""
        self._connectors[connector.payer_id] = connector
        logger.info("payer.connector.registered", extra={"payer": connector.payer_id})

    def list_payers(self) -> list[dict[str, Any]]:
        """List all registered payer connectors."""
        return [
            {
                "payer_id": c.payer_id,
                "payer_name": c.payer_name,
                "supports_real_time": c.supports_real_time,
            }
            for c in self._connectors.values()
        ]


# Module-level singleton
payer_registry = PayerConnectorRegistry()
