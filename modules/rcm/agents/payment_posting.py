"""
Eminence HealthOS — Payment Posting Agent (#50)
Layer 5 (Measurement): Reconciles payments, identifies underpayments,
flags discrepancies, and tracks accounts receivable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)


class PaymentPostingAgent(BaseAgent):
    """Reconciles payments, detects underpayments, and tracks AR aging."""

    name = "payment_posting"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = (
        "Automated payment reconciliation — identifies underpayments, "
        "flags discrepancies, and tracks accounts receivable aging"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "post_payment")

        if action == "post_payment":
            return self._post_payment(input_data)
        elif action == "reconcile_era":
            return self._reconcile_era(input_data)
        elif action == "underpayment_check":
            return self._underpayment_check(input_data)
        elif action == "ar_aging_report":
            return self._ar_aging_report(input_data)
        elif action == "collections_summary":
            return self._collections_summary(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown payment posting action: {action}",
                status=AgentStatus.FAILED,
            )

    def _post_payment(self, input_data: AgentInput) -> AgentOutput:
        """Post a payment against a claim and update balance."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        claim_id = ctx.get("claim_id", str(uuid.uuid4()))
        billed_amount = ctx.get("billed_amount", 0.0)
        paid_amount = ctx.get("paid_amount", 0.0)
        adjustment_amount = ctx.get("adjustment_amount", 0.0)
        patient_responsibility = ctx.get("patient_responsibility", 0.0)

        remaining_balance = round(billed_amount - paid_amount - adjustment_amount - patient_responsibility, 2)
        is_paid_in_full = remaining_balance <= 0.01
        is_underpaid = paid_amount < (billed_amount - adjustment_amount - patient_responsibility) * 0.95

        result = {
            "posting_id": str(uuid.uuid4()),
            "claim_id": claim_id,
            "posted_at": now.isoformat(),
            "billed_amount": billed_amount,
            "paid_amount": paid_amount,
            "adjustment_amount": adjustment_amount,
            "patient_responsibility": patient_responsibility,
            "remaining_balance": max(remaining_balance, 0),
            "is_paid_in_full": is_paid_in_full,
            "is_underpaid": is_underpaid,
            "status": "paid_in_full" if is_paid_in_full else ("underpaid" if is_underpaid else "partial_payment"),
            "next_action": None if is_paid_in_full else (
                "Review for underpayment appeal" if is_underpaid else "Bill patient responsibility"
            ),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=(
                f"Payment posted: ${paid_amount} on ${billed_amount} claim — "
                f"{'paid in full' if is_paid_in_full else f'balance ${max(remaining_balance, 0)}'}"
            ),
        )

    def _reconcile_era(self, input_data: AgentInput) -> AgentOutput:
        """Reconcile an Electronic Remittance Advice (ERA/835) against claims."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        era_id = ctx.get("era_id", str(uuid.uuid4()))
        line_items = ctx.get("line_items", [])

        matched = 0
        unmatched = 0
        discrepancies: list[dict[str, Any]] = []
        total_paid = 0.0

        for item in line_items:
            claim_id = item.get("claim_id", "")
            expected = item.get("expected_amount", 0.0)
            paid = item.get("paid_amount", 0.0)
            total_paid += paid

            if abs(expected - paid) < 0.01:
                matched += 1
            elif paid > 0:
                matched += 1
                if paid < expected * 0.90:
                    discrepancies.append({
                        "claim_id": claim_id,
                        "expected": expected,
                        "paid": paid,
                        "difference": round(expected - paid, 2),
                        "type": "underpayment",
                    })
            else:
                unmatched += 1

        # Demo data
        if not line_items:
            matched, unmatched = 45, 3
            total_paid = 28450.00
            discrepancies = [
                {"claim_id": "CLM-1234", "expected": 850.00, "paid": 680.00, "difference": 170.00, "type": "underpayment"},
                {"claim_id": "CLM-1891", "expected": 425.00, "paid": 340.00, "difference": 85.00, "type": "underpayment"},
            ]

        result = {
            "era_id": era_id,
            "reconciled_at": now.isoformat(),
            "total_line_items": len(line_items) or (matched + unmatched),
            "matched": matched,
            "unmatched": unmatched,
            "total_paid": round(total_paid, 2),
            "discrepancies": discrepancies,
            "discrepancy_amount": round(sum(d["difference"] for d in discrepancies), 2),
            "reconciliation_status": "clean" if not discrepancies else "discrepancies_found",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=(
                f"ERA reconciled: {matched} matched, {unmatched} unmatched, "
                f"{len(discrepancies)} discrepancies"
            ),
        )

    def _underpayment_check(self, input_data: AgentInput) -> AgentOutput:
        """Check for systematic underpayments by payer."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        payments = ctx.get("payments", [])

        payer_analysis: dict[str, dict[str, Any]] = {}

        for payment in payments:
            payer = payment.get("payer", "Unknown")
            expected = payment.get("expected", 0.0)
            paid = payment.get("paid", 0.0)

            if payer not in payer_analysis:
                payer_analysis[payer] = {"total_expected": 0.0, "total_paid": 0.0, "claim_count": 0, "underpayments": 0}

            payer_analysis[payer]["total_expected"] += expected
            payer_analysis[payer]["total_paid"] += paid
            payer_analysis[payer]["claim_count"] += 1
            if paid < expected * 0.95:
                payer_analysis[payer]["underpayments"] += 1

        # Defaults
        if not payer_analysis:
            payer_analysis = {
                "Blue Cross": {"total_expected": 125000, "total_paid": 118750, "claim_count": 312, "underpayments": 24},
                "Aetna": {"total_expected": 89000, "total_paid": 86830, "claim_count": 198, "underpayments": 12},
                "UnitedHealth": {"total_expected": 156000, "total_paid": 146640, "claim_count": 420, "underpayments": 38},
                "Medicare": {"total_expected": 234000, "total_paid": 231660, "claim_count": 856, "underpayments": 15},
            }

        payer_summary = []
        total_underpayment = 0.0
        for payer, data in payer_analysis.items():
            diff = data["total_expected"] - data["total_paid"]
            total_underpayment += diff
            payer_summary.append({
                "payer": payer,
                "claim_count": data["claim_count"],
                "total_expected": round(data["total_expected"], 2),
                "total_paid": round(data["total_paid"], 2),
                "underpayment_amount": round(diff, 2),
                "payment_rate_pct": round(data["total_paid"] / max(data["total_expected"], 0.01) * 100, 1),
                "underpayment_count": data["underpayments"],
            })

        result = {
            "analyzed_at": now.isoformat(),
            "period": ctx.get("period", "last_90_days"),
            "payer_summary": sorted(payer_summary, key=lambda x: x["underpayment_amount"], reverse=True),
            "total_underpayment": round(total_underpayment, 2),
            "action_required": total_underpayment > 5000,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Underpayment analysis: ${round(total_underpayment, 2)} across {len(payer_analysis)} payers",
        )

    def _ar_aging_report(self, input_data: AgentInput) -> AgentOutput:
        """Generate accounts receivable aging report."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        buckets = ctx.get("buckets", {
            "0_30": {"count": 245, "amount": 187500.00},
            "31_60": {"count": 128, "amount": 96400.00},
            "61_90": {"count": 67, "amount": 52300.00},
            "91_120": {"count": 34, "amount": 28100.00},
            "over_120": {"count": 19, "amount": 15800.00},
        })

        total_ar = sum(b["amount"] for b in buckets.values())
        total_claims = sum(b["count"] for b in buckets.values())

        result = {
            "report_date": now.isoformat(),
            "total_ar": round(total_ar, 2),
            "total_claims": total_claims,
            "aging_buckets": {
                k: {
                    **v,
                    "pct_of_total": round(v["amount"] / max(total_ar, 0.01) * 100, 1),
                }
                for k, v in buckets.items()
            },
            "days_in_ar_average": 42.5,
            "over_90_pct": round(
                (buckets.get("91_120", {}).get("amount", 0) + buckets.get("over_120", {}).get("amount", 0))
                / max(total_ar, 0.01) * 100,
                1,
            ),
            "benchmark": {
                "days_in_ar_target": 35,
                "over_90_target_pct": 10.0,
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"AR aging: ${round(total_ar, 2)} total, {total_claims} claims, avg 42.5 days",
        )

    def _collections_summary(self, input_data: AgentInput) -> AgentOutput:
        """Summary of collection performance metrics."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "period": ctx.get("period", "current_month"),
            "report_date": now.isoformat(),
            "total_billed": ctx.get("total_billed", 485000.00),
            "total_collected": ctx.get("total_collected", 428000.00),
            "collection_rate": round(ctx.get("total_collected", 428000) / max(ctx.get("total_billed", 485000), 1) * 100, 1),
            "net_collection_rate": 96.2,
            "adjustments": ctx.get("adjustments", 42000.00),
            "write_offs": ctx.get("write_offs", 15000.00),
            "patient_payments": ctx.get("patient_payments", 38500.00),
            "payer_mix": {
                "commercial": {"pct": 42, "collection_rate": 94.5},
                "medicare": {"pct": 35, "collection_rate": 97.8},
                "medicaid": {"pct": 15, "collection_rate": 88.2},
                "self_pay": {"pct": 8, "collection_rate": 45.6},
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Collections: ${result['total_collected']:,.0f} collected ({result['collection_rate']}% rate)",
        )
