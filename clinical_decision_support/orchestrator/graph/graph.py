from .state import GraphState
from langgraph.graph import StateGraph, END, START

from tools.mcp_client import MCPClient
from fhir.mappers import obs_hr, obs_rr, obs_spo2, obs_temp, obs_weight, obs_bp_panel
import httpx

mcp = MCPClient("http://mcp-fhir-adapter:8002", "dev-key")

BACKEND_INTERNAL = "http://backend:8000"


# Clinical thresholds for vital signs
VITALS_THRESHOLDS = {
    "HR": {"low": 60, "high": 100, "critical_low": 50, "critical_high": 120},
    "RR": {"low": 12, "high": 20, "critical_low": 8, "critical_high": 30},
    "SpO2": {"low": 95, "critical_low": 90},
    "TempC": {"low": 36.1, "high": 37.5, "critical_low": 35.0, "critical_high": 38.5},
    "BP_SYS": {"low": 90, "high": 140, "critical_low": 80, "critical_high": 180},
    "BP_DIA": {"low": 60, "high": 90, "critical_low": 50, "critical_high": 120},
}


def analyze_vitals(readings: dict) -> dict:
    """Analyze vital signs and generate appropriate recommendation."""
    findings = []
    evidence = []
    severity = "info"

    # Heart Rate analysis
    hr = readings.get("HR")
    if hr is not None:
        if hr >= VITALS_THRESHOLDS["HR"]["critical_high"]:
            findings.append(f"Critical tachycardia (HR: {hr} bpm)")
            evidence.append({"source": "Heart Rate Monitor", "snippet": f"HR {hr} bpm exceeds critical threshold of 120 bpm"})
            severity = "critical"
        elif hr >= VITALS_THRESHOLDS["HR"]["high"]:
            findings.append(f"Elevated heart rate (HR: {hr} bpm)")
            evidence.append({"source": "Heart Rate Monitor", "snippet": f"HR {hr} bpm above normal range (60-100)"})
            severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))
        elif hr <= VITALS_THRESHOLDS["HR"]["critical_low"]:
            findings.append(f"Critical bradycardia (HR: {hr} bpm)")
            evidence.append({"source": "Heart Rate Monitor", "snippet": f"HR {hr} bpm below critical threshold of 50 bpm"})
            severity = "critical"
        elif hr <= VITALS_THRESHOLDS["HR"]["low"]:
            findings.append(f"Low heart rate (HR: {hr} bpm)")
            evidence.append({"source": "Heart Rate Monitor", "snippet": f"HR {hr} bpm below normal range (60-100)"})
            severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))

    # SpO2 analysis
    spo2 = readings.get("SpO2")
    if spo2 is not None:
        if spo2 <= VITALS_THRESHOLDS["SpO2"]["critical_low"]:
            findings.append(f"Critical hypoxemia (SpO2: {spo2}%)")
            evidence.append({"source": "Pulse Oximeter", "snippet": f"SpO2 {spo2}% indicates severe oxygen desaturation"})
            severity = "critical"
        elif spo2 <= VITALS_THRESHOLDS["SpO2"]["low"]:
            findings.append(f"Low oxygen saturation (SpO2: {spo2}%)")
            evidence.append({"source": "Pulse Oximeter", "snippet": f"SpO2 {spo2}% below normal threshold of 95%"})
            severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))

    # Temperature analysis
    temp = readings.get("TempC")
    if temp is not None:
        if temp >= VITALS_THRESHOLDS["TempC"]["critical_high"]:
            findings.append(f"High fever (Temp: {temp}°C)")
            evidence.append({"source": "Thermometer", "snippet": f"Temperature {temp}°C indicates significant fever"})
            severity = "critical"
        elif temp >= VITALS_THRESHOLDS["TempC"]["high"]:
            findings.append(f"Elevated temperature (Temp: {temp}°C)")
            evidence.append({"source": "Thermometer", "snippet": f"Temperature {temp}°C above normal range"})
            severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))
        elif temp <= VITALS_THRESHOLDS["TempC"]["critical_low"]:
            findings.append(f"Hypothermia (Temp: {temp}°C)")
            evidence.append({"source": "Thermometer", "snippet": f"Temperature {temp}°C indicates hypothermia"})
            severity = "critical"

    # Blood Pressure analysis
    bp_sys = readings.get("BP_SYS")
    bp_dia = readings.get("BP_DIA")
    if bp_sys is not None and bp_dia is not None:
        if bp_sys >= VITALS_THRESHOLDS["BP_SYS"]["critical_high"] or bp_dia >= VITALS_THRESHOLDS["BP_DIA"]["critical_high"]:
            findings.append(f"Hypertensive crisis (BP: {bp_sys}/{bp_dia} mmHg)")
            evidence.append({"source": "Blood Pressure Monitor", "snippet": f"BP {bp_sys}/{bp_dia} mmHg requires immediate attention"})
            severity = "critical"
        elif bp_sys >= VITALS_THRESHOLDS["BP_SYS"]["high"] or bp_dia >= VITALS_THRESHOLDS["BP_DIA"]["high"]:
            findings.append(f"Elevated blood pressure (BP: {bp_sys}/{bp_dia} mmHg)")
            evidence.append({"source": "Blood Pressure Monitor", "snippet": f"BP {bp_sys}/{bp_dia} mmHg above normal range"})
            severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))
        elif bp_sys <= VITALS_THRESHOLDS["BP_SYS"]["critical_low"]:
            findings.append(f"Hypotension (BP: {bp_sys}/{bp_dia} mmHg)")
            evidence.append({"source": "Blood Pressure Monitor", "snippet": f"Systolic BP {bp_sys} mmHg critically low"})
            severity = "critical"

    # Respiratory Rate analysis
    rr = readings.get("RR")
    if rr is not None:
        if rr >= VITALS_THRESHOLDS["RR"]["critical_high"]:
            findings.append(f"Severe tachypnea (RR: {rr}/min)")
            evidence.append({"source": "Respiratory Monitor", "snippet": f"RR {rr}/min indicates respiratory distress"})
            severity = "critical"
        elif rr >= VITALS_THRESHOLDS["RR"]["high"]:
            findings.append(f"Elevated respiratory rate (RR: {rr}/min)")
            evidence.append({"source": "Respiratory Monitor", "snippet": f"RR {rr}/min above normal range"})
            severity = max(severity, "warning", key=lambda x: ["info", "warning", "critical"].index(x))
        elif rr <= VITALS_THRESHOLDS["RR"]["critical_low"]:
            findings.append(f"Bradypnea (RR: {rr}/min)")
            evidence.append({"source": "Respiratory Monitor", "snippet": f"RR {rr}/min critically low"})
            severity = "critical"

    # Generate recommendation based on findings
    if not findings:
        return {
            "severity": "info",
            "title": "Vitals Within Normal Range",
            "summary": "All vital signs are within normal parameters. Continue routine monitoring.",
            "actions": [{"type": "monitor", "description": "Continue routine monitoring"}],
            "rationale": "No abnormal values detected in current vital signs assessment.",
            "evidence": [],
            "confidence": 0.95
        }

    # Build recommendation based on severity
    if severity == "critical":
        title = "Critical Vitals Alert"
        summary = f"Immediate attention required: {'; '.join(findings)}"
        actions = [
            {"type": "alert", "description": "Notify physician immediately"},
            {"type": "assess", "description": "Perform bedside assessment"},
            {"type": "monitor", "description": "Increase monitoring frequency"}
        ]
    elif severity == "warning":
        title = "Abnormal Vitals Detected"
        summary = f"Review recommended: {'; '.join(findings)}"
        actions = [
            {"type": "review", "description": "Clinical review recommended"},
            {"type": "monitor", "description": "Increase monitoring frequency"}
        ]
    else:
        title = "Minor Vitals Variation"
        summary = f"Minor variations noted: {'; '.join(findings)}"
        actions = [{"type": "monitor", "description": "Continue monitoring"}]

    return {
        "severity": severity,
        "title": title,
        "summary": summary,
        "actions": actions,
        "rationale": f"Analysis based on {len(findings)} finding(s) from current vital signs.",
        "evidence": evidence,
        "confidence": 0.85
    }


async def identity_node(state: GraphState):
    # Use actual device_id from state if available
    device_id = state.device_id or "deviceX"
    res = await mcp.call("resolve_patient_encounter", {
        "facility_id": "facility1",
        "device_id": device_id,
        "observed_at": state.effective_time or "2026-01-01T00:00:00Z"
    })
    state.patient_id = res.get("patient_id", "demo-patient")
    return state


async def manager_node(state: GraphState):
    """Analyze vitals and generate intelligent recommendations."""
    readings = state.readings or {}
    state.recommendation = analyze_vitals(readings)
    return state


async def writeback_node(state: GraphState):
    patient_id = state.patient_id
    encounter_id = None
    device_id = state.device_id or "deviceX"
    t = state.effective_time or "2026-01-01T00:00:00Z"

    readings = state.readings or {}
    payloads = [
        obs_hr(patient_id, encounter_id, t, device_id, readings.get("HR", 72)),
        obs_rr(patient_id, encounter_id, t, device_id, readings.get("RR", 14)),
        obs_spo2(patient_id, encounter_id, t, device_id, readings.get("SpO2", 98)),
        obs_temp(patient_id, encounter_id, t, device_id, readings.get("TempC", 36.7)),
        obs_weight(patient_id, encounter_id, t, device_id, readings.get("WeightKg", 82.5)),
        obs_bp_panel(patient_id, encounter_id, t, device_id, readings.get("BP_SYS", 120), readings.get("BP_DIA", 78)),
    ]

    created = []
    for o in payloads:
        res = await mcp.call("write_fhir_observation", {"observation": o})
        created.append(res)

    state.recommendation = state.recommendation or {}
    state.recommendation["fhir_writeback"] = created
    return state


async def persist_node(state: GraphState):
    """Persist the recommendation to the backend database."""
    if not state.recommendation:
        return state

    recommendation_data = {
        "patient_id": state.patient_id,
        "severity": state.recommendation.get("severity", "info"),
        "title": state.recommendation.get("title", "Vitals Assessment"),
        "summary": state.recommendation.get("summary", ""),
        "actions": state.recommendation.get("actions", []),
        "rationale": state.recommendation.get("rationale", ""),
        "evidence": state.recommendation.get("evidence", []),
        "confidence": state.recommendation.get("confidence", 0.0),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{BACKEND_INTERNAL}/api/v1/recommendations/",
            json=recommendation_data
        )
        r.raise_for_status()
        state.recommendation["persisted"] = r.json()

    return state


# Build the graph
graph = StateGraph(GraphState)
graph.add_node("identity", identity_node)
graph.add_node("manager", manager_node)
graph.add_node("writeback", writeback_node)
graph.add_node("persist", persist_node)
graph.add_edge(START, "identity")
graph.add_edge("identity", "manager")
graph.add_edge("manager", "writeback")
graph.add_edge("writeback", "persist")
graph.add_edge("persist", END)

app_graph = graph.compile()


async def run_graph(vitals_event_id):
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{BACKEND_INTERNAL}/api/v1/vitals/internal/events/{vitals_event_id}")
        r.raise_for_status()
        event = r.json()

    state = GraphState(vitals_event_id=vitals_event_id)
    state.device_id = event.get("device_id", "unknown")
    state.effective_time = event.get("effective_time")
    state.readings = event.get("readings", {})
    return await app_graph.ainvoke(state)
