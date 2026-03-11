"""Event type constants used across the platform."""


class EventTypes:
    # Vitals
    VITAL_RECORDED = "vital.recorded"
    VITAL_ABNORMAL = "vital.abnormal"
    VITAL_CRITICAL = "vital.critical"

    # Labs
    LAB_RESULT_RECEIVED = "lab.result_received"
    LAB_RESULT_ABNORMAL = "lab.result_abnormal"

    # Devices
    DEVICE_DATA_RECEIVED = "device.data_received"
    DEVICE_ALERT = "device.alert"
    DEVICE_DISCONNECTED = "device.disconnected"

    # Agents
    AGENT_DECISION_MADE = "agent.decision_made"
    AGENT_ESCALATION = "agent.escalation"
    AGENT_HITL_REQUEST = "agent.hitl_request"

    # Alerts
    ALERT_CREATED = "alert.created"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"
    ALERT_RESOLVED = "alert.resolved"
    ALERT_ESCALATED = "alert.escalated"

    # Patient
    PATIENT_RISK_UPDATED = "patient.risk_updated"
    PATIENT_CARE_PLAN_GENERATED = "patient.care_plan_generated"

    # Medication
    MEDICATION_PRESCRIBED = "medication.prescribed"
    MEDICATION_INTERACTION_DETECTED = "medication.interaction_detected"

    # Audit
    AUDIT_EVENT = "audit.event"
    PHI_ACCESS = "audit.phi_access"
