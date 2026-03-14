"""
Eminence HealthOS — HIPAA Compliance Monitor Agent (#67)
Layer 5 (Measurement): Continuous automated HIPAA compliance scanning across
all platform operations, covering administrative, physical, and technical safeguards.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import json
import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

# ── HIPAA Controls mapped to 45 CFR sections ────────────────────────────────

HIPAA_CONTROLS: dict[str, dict[str, Any]] = {
    # Administrative Safeguards — 45 CFR 164.308
    "security_management_process": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(1)",
        "title": "Security Management Process",
        "description": "Implement policies and procedures to prevent, detect, contain, and correct security violations",
    },
    "assigned_security_responsibility": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(2)",
        "title": "Assigned Security Responsibility",
        "description": "Identify the security official responsible for developing and implementing policies",
    },
    "workforce_security": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(3)",
        "title": "Workforce Security",
        "description": "Implement policies to ensure workforce members have appropriate access to ePHI",
    },
    "information_access_management": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(4)",
        "title": "Information Access Management",
        "description": "Implement policies authorizing access to ePHI consistent with the Privacy Rule",
    },
    "security_awareness_training": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(5)",
        "title": "Security Awareness and Training",
        "description": "Implement a security awareness and training program for all workforce members",
    },
    "security_incident_procedures": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(6)",
        "title": "Security Incident Procedures",
        "description": "Implement policies to address security incidents",
    },
    "contingency_plan": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(7)",
        "title": "Contingency Plan",
        "description": "Establish policies for responding to an emergency or other occurrence that damages ePHI systems",
    },
    "evaluation": {
        "category": "administrative",
        "cfr": "45 CFR 164.308(a)(8)",
        "title": "Evaluation",
        "description": "Perform periodic technical and non-technical evaluations of security policies",
    },
    # Physical Safeguards — 45 CFR 164.310
    "facility_access_controls": {
        "category": "physical",
        "cfr": "45 CFR 164.310(a)",
        "title": "Facility Access Controls",
        "description": "Implement policies to limit physical access to electronic information systems",
    },
    "workstation_use": {
        "category": "physical",
        "cfr": "45 CFR 164.310(b)",
        "title": "Workstation Use",
        "description": "Implement policies specifying proper functions, physical attributes, and workstation surroundings",
    },
    "workstation_security": {
        "category": "physical",
        "cfr": "45 CFR 164.310(c)",
        "title": "Workstation Security",
        "description": "Implement physical safeguards for all workstations that access ePHI",
    },
    "device_and_media_controls": {
        "category": "physical",
        "cfr": "45 CFR 164.310(d)",
        "title": "Device and Media Controls",
        "description": "Implement policies governing receipt and removal of hardware and electronic media containing ePHI",
    },
    # Technical Safeguards — 45 CFR 164.312
    "access_control": {
        "category": "technical",
        "cfr": "45 CFR 164.312(a)",
        "title": "Access Control",
        "description": "Implement technical policies to allow access only to authorized persons or software programs",
    },
    "audit_controls": {
        "category": "technical",
        "cfr": "45 CFR 164.312(b)",
        "title": "Audit Controls",
        "description": "Implement hardware, software, and procedural mechanisms to record and examine access to ePHI",
    },
    "integrity": {
        "category": "technical",
        "cfr": "45 CFR 164.312(c)",
        "title": "Integrity",
        "description": "Implement policies to protect ePHI from improper alteration or destruction",
    },
    "transmission_security": {
        "category": "technical",
        "cfr": "45 CFR 164.312(e)",
        "title": "Transmission Security",
        "description": "Implement technical security measures to guard against unauthorized access to ePHI transmitted over a network",
    },
}


class HIPAAComplianceMonitorAgent(BaseAgent):
    """Continuous automated HIPAA compliance scanning across all platform operations."""

    name = "hipaa_compliance_monitor"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = (
        "Continuous automated HIPAA compliance scanning covering administrative, "
        "physical, and technical safeguards per 45 CFR 164"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "full_scan")

        if action == "full_scan":
            return await self._full_scan(input_data)
        elif action == "access_audit":
            return await self._access_audit(input_data)
        elif action == "phi_exposure_check":
            return await self._phi_exposure_check(input_data)
        elif action == "policy_compliance":
            return await self._policy_compliance(input_data)
        elif action == "breach_detection":
            return await self._breach_detection(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown HIPAA compliance action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Full Scan ────────────────────────────────────────────────────────────

    async def _full_scan(self, input_data: AgentInput) -> AgentOutput:
        """Run all three HIPAA safeguard categories — administrative, physical, technical."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        categories: dict[str, list[dict[str, Any]]] = {
            "administrative": [],
            "physical": [],
            "technical": [],
        }

        total_pass = 0
        total_fail = 0
        findings: list[dict[str, Any]] = []

        for control_id, control in HIPAA_CONTROLS.items():
            category = control["category"]
            # Check if the caller supplied explicit control overrides
            override = ctx.get("control_overrides", {}).get(control_id)
            passed = override if override is not None else self._evaluate_control(control_id, ctx)

            check_result = {
                "control_id": control_id,
                "title": control["title"],
                "cfr": control["cfr"],
                "status": "pass" if passed else "fail",
                "details": control["description"],
                "evaluated_at": now.isoformat(),
            }
            categories[category].append(check_result)

            if passed:
                total_pass += 1
            else:
                total_fail += 1
                findings.append({
                    "control_id": control_id,
                    "cfr": control["cfr"],
                    "title": control["title"],
                    "severity": "high" if category == "technical" else "medium",
                    "remediation": f"Review and remediate {control['title']} per {control['cfr']}",
                })

        total_controls = total_pass + total_fail
        compliance_rate = round(total_pass / max(total_controls, 1) * 100, 1)

        result = {
            "scan_type": "full_scan",
            "scan_timestamp": now.isoformat(),
            "summary": {
                "total_controls": total_controls,
                "passed": total_pass,
                "failed": total_fail,
                "compliance_rate": compliance_rate,
            },
            "categories": {
                cat: {
                    "checks": checks,
                    "passed": sum(1 for c in checks if c["status"] == "pass"),
                    "failed": sum(1 for c in checks if c["status"] == "fail"),
                }
                for cat, checks in categories.items()
            },
            "findings": sorted(findings, key=lambda f: f["severity"] == "high", reverse=True),
        }

        confidence = 0.95 if compliance_rate >= 90 else (0.85 if compliance_rate >= 70 else 0.70)

        # ── LLM: generate compliance narrative ───────────────────────────────
        try:
            prompt = (
                "You are a HIPAA compliance expert. Based on the following full compliance "
                "scan results, produce a concise narrative (2-3 paragraphs) providing a risk "
                "assessment, highlighting the most critical findings, and prioritizing "
                "remediation actions.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered HIPAA compliance analyst for a healthcare platform. "
                    "Provide expert risk assessment and remediation priorities per 45 CFR 164."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["compliance_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for full_scan; continuing without narrative")
            result["compliance_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"HIPAA full scan: {compliance_rate}% compliant — "
                f"{total_pass}/{total_controls} controls passed, {total_fail} findings"
            ),
        )

    # ── Access Audit ─────────────────────────────────────────────────────────

    async def _access_audit(self, input_data: AgentInput) -> AgentOutput:
        """Analyze access logs for anomalous patterns."""
        ctx = input_data.context
        access_logs = ctx.get("access_logs", [])
        now = datetime.now(timezone.utc)

        anomalies: list[dict[str, Any]] = []
        total_events = len(access_logs)

        for entry in access_logs:
            issues: list[str] = []

            # Unusual hours check (outside 6 AM - 10 PM)
            access_hour = entry.get("hour")
            if access_hour is not None and (access_hour < 6 or access_hour > 22):
                issues.append("off_hours_access")

            # Bulk data access check
            records_accessed = entry.get("records_accessed", 0)
            if records_accessed > 100:
                issues.append("bulk_data_access")

            # Cross-department access check
            user_dept = entry.get("user_department", "")
            resource_dept = entry.get("resource_department", "")
            if user_dept and resource_dept and user_dept != resource_dept:
                issues.append("cross_department_access")

            if issues:
                anomalies.append({
                    "user_id": entry.get("user_id", "unknown"),
                    "timestamp": entry.get("timestamp", now.isoformat()),
                    "resource": entry.get("resource", "unknown"),
                    "issues": issues,
                    "risk_level": "high" if len(issues) > 1 else "medium",
                    "records_accessed": records_accessed,
                })

        anomaly_rate = round(len(anomalies) / max(total_events, 1) * 100, 1)

        result = {
            "audit_type": "access_audit",
            "audit_timestamp": now.isoformat(),
            "total_events_analyzed": total_events,
            "anomalies_detected": len(anomalies),
            "anomaly_rate_percent": anomaly_rate,
            "anomalies": sorted(anomalies, key=lambda a: a["risk_level"] == "high", reverse=True),
            "patterns": {
                "off_hours_access": sum(1 for a in anomalies if "off_hours_access" in a["issues"]),
                "bulk_data_access": sum(1 for a in anomalies if "bulk_data_access" in a["issues"]),
                "cross_department_access": sum(1 for a in anomalies if "cross_department_access" in a["issues"]),
            },
        }

        confidence = 0.90 if total_events > 0 else 0.50

        # ── LLM: generate compliance narrative ───────────────────────────────
        try:
            prompt = (
                "You are a HIPAA access audit specialist. Based on the following access "
                "audit results, produce a concise narrative (2-3 paragraphs) assessing the "
                "risk level of detected anomalies, identifying patterns of concern, and "
                "recommending remediation priorities.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered HIPAA compliance analyst for a healthcare platform. "
                    "Provide expert risk assessment and remediation priorities per 45 CFR 164."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["compliance_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for access_audit; continuing without narrative")
            result["compliance_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Access audit: {len(anomalies)} anomalies in {total_events} events "
                f"({anomaly_rate}% anomaly rate)"
            ),
        )

    # ── PHI Exposure Check ───────────────────────────────────────────────────

    async def _phi_exposure_check(self, input_data: AgentInput) -> AgentOutput:
        """Scan data for unprotected PHI in logs, error messages, and API responses."""
        ctx = input_data.context
        scan_targets = ctx.get("scan_targets", [])
        now = datetime.now(timezone.utc)

        phi_patterns = [
            {"pattern": "ssn", "label": "Social Security Number", "severity": "critical"},
            {"pattern": "mrn", "label": "Medical Record Number", "severity": "high"},
            {"pattern": "dob", "label": "Date of Birth", "severity": "high"},
            {"pattern": "patient_name", "label": "Patient Name", "severity": "high"},
            {"pattern": "address", "label": "Physical Address", "severity": "medium"},
            {"pattern": "phone", "label": "Phone Number", "severity": "medium"},
            {"pattern": "email", "label": "Email Address", "severity": "medium"},
            {"pattern": "insurance_id", "label": "Insurance ID", "severity": "high"},
            {"pattern": "diagnosis", "label": "Diagnosis Information", "severity": "high"},
            {"pattern": "medication", "label": "Medication Information", "severity": "medium"},
        ]

        exposures: list[dict[str, Any]] = []

        for target in scan_targets:
            source = target.get("source", "unknown")
            content = target.get("content", "")
            content_lower = content.lower() if isinstance(content, str) else ""

            for phi in phi_patterns:
                if phi["pattern"] in content_lower:
                    exposures.append({
                        "source": source,
                        "phi_type": phi["label"],
                        "severity": phi["severity"],
                        "location": target.get("location", "unspecified"),
                        "remediation": f"Remove or encrypt {phi['label']} in {source}",
                    })

        critical_count = sum(1 for e in exposures if e["severity"] == "critical")
        high_count = sum(1 for e in exposures if e["severity"] == "high")

        result = {
            "check_type": "phi_exposure",
            "check_timestamp": now.isoformat(),
            "targets_scanned": len(scan_targets),
            "total_exposures": len(exposures),
            "severity_breakdown": {
                "critical": critical_count,
                "high": high_count,
                "medium": sum(1 for e in exposures if e["severity"] == "medium"),
            },
            "exposures": sorted(
                exposures,
                key=lambda e: {"critical": 0, "high": 1, "medium": 2}.get(e["severity"], 3),
            ),
            "phi_patterns_checked": [p["label"] for p in phi_patterns],
        }

        confidence = 0.88 if scan_targets else 0.50

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"PHI exposure check: {len(exposures)} exposures in {len(scan_targets)} targets — "
                f"{critical_count} critical, {high_count} high"
            ),
        )

    # ── Policy Compliance ────────────────────────────────────────────────────

    def _policy_compliance(self, input_data: AgentInput) -> AgentOutput:
        """Validate organizational policies against HIPAA requirements."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        required_policies = {
            "business_associate_agreements": {
                "requirement": "BAAs must be in place with all vendors handling PHI",
                "cfr": "45 CFR 164.308(b)(1)",
                "category": "administrative",
            },
            "workforce_training": {
                "requirement": "All workforce members must receive HIPAA training within 30 days of hire and annually thereafter",
                "cfr": "45 CFR 164.308(a)(5)",
                "category": "administrative",
            },
            "incident_response_plan": {
                "requirement": "Documented incident response plan with defined roles and notification procedures",
                "cfr": "45 CFR 164.308(a)(6)",
                "category": "administrative",
            },
            "risk_assessment": {
                "requirement": "Annual risk assessment identifying vulnerabilities and threats to ePHI",
                "cfr": "45 CFR 164.308(a)(1)(ii)(A)",
                "category": "administrative",
            },
            "data_backup_plan": {
                "requirement": "Procedures to create and maintain retrievable exact copies of ePHI",
                "cfr": "45 CFR 164.308(a)(7)(ii)(A)",
                "category": "administrative",
            },
            "access_control_policy": {
                "requirement": "Documented access control policy with role-based access and periodic review",
                "cfr": "45 CFR 164.312(a)(1)",
                "category": "technical",
            },
            "encryption_policy": {
                "requirement": "Encryption of ePHI at rest and in transit using approved algorithms",
                "cfr": "45 CFR 164.312(a)(2)(iv)",
                "category": "technical",
            },
            "breach_notification_policy": {
                "requirement": "Breach notification within 60 days of discovery for breaches affecting 500+ individuals",
                "cfr": "45 CFR 164.404",
                "category": "administrative",
            },
        }

        org_policies = ctx.get("policies", {})
        compliant: list[dict[str, Any]] = []
        non_compliant: list[dict[str, Any]] = []

        for policy_id, policy_req in required_policies.items():
            org_policy = org_policies.get(policy_id, {})
            has_policy = org_policy.get("exists", False)
            last_reviewed = org_policy.get("last_reviewed")
            is_current = False

            if last_reviewed:
                try:
                    reviewed_dt = datetime.fromisoformat(last_reviewed)
                    days_since = (now - reviewed_dt.replace(tzinfo=timezone.utc)).days
                    is_current = days_since <= 365
                except (ValueError, TypeError):
                    is_current = False

            status = "compliant" if (has_policy and is_current) else "non_compliant"
            entry = {
                "policy_id": policy_id,
                "cfr": policy_req["cfr"],
                "requirement": policy_req["requirement"],
                "category": policy_req["category"],
                "status": status,
                "has_policy": has_policy,
                "is_current": is_current,
                "last_reviewed": last_reviewed,
            }

            if status == "compliant":
                compliant.append(entry)
            else:
                non_compliant.append(entry)

        total = len(required_policies)
        compliance_rate = round(len(compliant) / max(total, 1) * 100, 1)

        result = {
            "check_type": "policy_compliance",
            "check_timestamp": now.isoformat(),
            "total_policies_required": total,
            "compliant_count": len(compliant),
            "non_compliant_count": len(non_compliant),
            "compliance_rate": compliance_rate,
            "compliant_policies": compliant,
            "non_compliant_policies": non_compliant,
        }

        confidence = 0.92 if org_policies else 0.60

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Policy compliance: {len(compliant)}/{total} policies compliant "
                f"({compliance_rate}%); {len(non_compliant)} gaps"
            ),
        )

    # ── Breach Detection ─────────────────────────────────────────────────────

    def _breach_detection(self, input_data: AgentInput) -> AgentOutput:
        """Evaluate potential breach indicators and classify severity."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        indicators = ctx.get("indicators", [])

        severity_weights = {
            "unauthorized_access": 3,
            "data_exfiltration": 4,
            "ransomware": 4,
            "lost_device": 2,
            "improper_disposal": 2,
            "insider_threat": 3,
            "phishing_success": 3,
            "system_compromise": 4,
            "unauthorized_disclosure": 3,
        }

        assessed_indicators: list[dict[str, Any]] = []
        total_weight = 0

        for indicator in indicators:
            indicator_type = indicator.get("type", "unknown")
            weight = severity_weights.get(indicator_type, 2)
            total_weight += weight

            records_affected = indicator.get("records_affected", 0)
            phi_involved = indicator.get("phi_involved", False)

            # Escalate weight for PHI involvement or large-scale impact
            if phi_involved:
                weight += 1
            if records_affected > 500:
                weight += 2
            elif records_affected > 0:
                weight += 1

            if weight >= 5:
                severity = "critical"
            elif weight >= 4:
                severity = "high"
            elif weight >= 3:
                severity = "medium"
            else:
                severity = "low"

            # Determine reporting timeline per HIPAA Breach Notification Rule
            if records_affected >= 500:
                reporting_deadline = "60 days from discovery — must notify HHS and media"
            elif records_affected > 0:
                reporting_deadline = "60 days from end of calendar year — annual HHS log submission"
            else:
                reporting_deadline = "Document internally — no external reporting required pending investigation"

            assessed_indicators.append({
                "type": indicator_type,
                "description": indicator.get("description", ""),
                "severity": severity,
                "weight": weight,
                "records_affected": records_affected,
                "phi_involved": phi_involved,
                "reporting_timeline": reporting_deadline,
                "detected_at": indicator.get("detected_at", now.isoformat()),
                "recommended_actions": self._breach_actions(severity),
            })

        overall_severity = "low"
        if any(i["severity"] == "critical" for i in assessed_indicators):
            overall_severity = "critical"
        elif any(i["severity"] == "high" for i in assessed_indicators):
            overall_severity = "high"
        elif any(i["severity"] == "medium" for i in assessed_indicators):
            overall_severity = "medium"

        result = {
            "assessment_type": "breach_detection",
            "assessment_timestamp": now.isoformat(),
            "total_indicators": len(indicators),
            "overall_severity": overall_severity,
            "indicators": sorted(
                assessed_indicators,
                key=lambda i: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(i["severity"], 4),
            ),
            "immediate_actions_required": overall_severity in ("critical", "high"),
            "hhs_notification_required": any(
                i["records_affected"] >= 500 for i in assessed_indicators
            ),
        }

        confidence = 0.90 if indicators else 0.50

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Breach detection: {len(indicators)} indicators assessed — "
                f"overall severity: {overall_severity}"
            ),
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _evaluate_control(control_id: str, ctx: dict[str, Any]) -> bool:
        """Evaluate a single HIPAA control. Returns True if passing."""
        statuses = ctx.get("control_statuses", {})
        if control_id in statuses:
            return bool(statuses[control_id])
        # Default: assume passing unless explicitly flagged
        failed_controls = ctx.get("failed_controls", [])
        return control_id not in failed_controls

    @staticmethod
    def _breach_actions(severity: str) -> list[str]:
        """Return recommended actions based on breach severity."""
        base = ["Document the incident in the breach log", "Preserve all relevant evidence"]
        if severity == "critical":
            return base + [
                "Activate incident response team immediately",
                "Notify Chief Privacy Officer within 1 hour",
                "Engage forensic investigation team",
                "Prepare HHS breach notification",
                "Notify affected individuals within 60 days",
                "Issue media notification if 500+ records affected",
            ]
        elif severity == "high":
            return base + [
                "Notify Chief Privacy Officer within 4 hours",
                "Initiate forensic investigation",
                "Assess scope of PHI exposure",
                "Prepare breach notification if warranted",
            ]
        elif severity == "medium":
            return base + [
                "Notify security team within 24 hours",
                "Conduct preliminary impact assessment",
                "Determine if formal breach notification is required",
            ]
        else:
            return base + [
                "Log incident for quarterly review",
                "Monitor for recurrence",
            ]
