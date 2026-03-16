from typing import Dict, Any, Optional
from datetime import datetime

CATEGORY_VITALS = [{
    "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
        "code": "vital-signs",
        "display": "Vital Signs"
    }]
}]

def _base_obs(patient_id: str, encounter_id: Optional[str], effective_time: str, device_id: str) -> Dict[str, Any]:
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "category": CATEGORY_VITALS,
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": effective_time,
        "device": {"reference": f"Device/{device_id}"},
    }
    if encounter_id:
        obs["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    return obs

def obs_hr(patient_id: str, encounter_id: Optional[str], effective_time: str, device_id: str, bpm: float) -> Dict[str, Any]:
    obs = _base_obs(patient_id, encounter_id, effective_time, device_id)
    obs["code"] = {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]}
    obs["valueQuantity"] = {"value": bpm, "system": "http://unitsofmeasure.org", "code": "{beats}/min"}
    return obs

def obs_rr(patient_id: str, encounter_id: Optional[str], effective_time: str, device_id: str, rpm: float) -> Dict[str, Any]:
    obs = _base_obs(patient_id, encounter_id, effective_time, device_id)
    obs["code"] = {"coding": [{"system": "http://loinc.org", "code": "9279-1", "display": "Respiratory rate"}]}
    obs["valueQuantity"] = {"value": rpm, "system": "http://unitsofmeasure.org", "code": "{breaths}/min"}
    return obs

def obs_spo2(patient_id: str, encounter_id: Optional[str], effective_time: str, device_id: str, pct: float) -> Dict[str, Any]:
    obs = _base_obs(patient_id, encounter_id, effective_time, device_id)
    obs["code"] = {"coding": [{"system": "http://loinc.org", "code": "59408-5", "display": "Oxygen saturation in Arterial blood by Pulse oximetry"}]}
    obs["valueQuantity"] = {"value": pct, "system": "http://unitsofmeasure.org", "code": "%"}
    return obs

def obs_temp(patient_id: str, encounter_id: Optional[str], effective_time: str, device_id: str, temp_c: float) -> Dict[str, Any]:
    obs = _base_obs(patient_id, encounter_id, effective_time, device_id)
    obs["code"] = {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]}
    obs["valueQuantity"] = {"value": temp_c, "system": "http://unitsofmeasure.org", "code": "Cel"}
    return obs

def obs_weight(patient_id: str, encounter_id: Optional[str], effective_time: str, device_id: str, kg: float) -> Dict[str, Any]:
    obs = _base_obs(patient_id, encounter_id, effective_time, device_id)
    obs["code"] = {"coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Body weight"}]}
    obs["valueQuantity"] = {"value": kg, "system": "http://unitsofmeasure.org", "code": "kg"}
    return obs

def obs_bp_panel(patient_id: str, encounter_id: Optional[str], effective_time: str, device_id: str, sys: float, dia: float) -> Dict[str, Any]:
    obs = _base_obs(patient_id, encounter_id, effective_time, device_id)
    obs["code"] = {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]}
    obs["component"] = [
        {
            "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
            "valueQuantity": {"value": sys, "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
        },
        {
            "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
            "valueQuantity": {"value": dia, "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
        }
    ]
    return obs

