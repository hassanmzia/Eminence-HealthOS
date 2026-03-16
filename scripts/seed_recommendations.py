#!/usr/bin/env python3
"""
Eminence HealthOS - AI Recommendations Seed Script

Populates the database with realistic AI recommendations from various agents
so the dashboard AI Recommendations panel has data to display.

Run after seed_data.py:
  python scripts/seed_recommendations.py
  python scripts/seed_recommendations.py --api-url http://localhost:4090
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

API_BASE_URL = os.environ.get("HEALTHOS_API_URL", "http://localhost:4090")

# ---------------------------------------------------------------------------
# Recommendation definitions — realistic clinical AI recommendations
# ---------------------------------------------------------------------------

RECOMMENDATIONS = [
    {
        "agent_type": "medication",
        "title": "Potential Drug Interaction: Metformin + Furosemide",
        "recommendation": "Patient is on Metformin 500mg and Furosemide 40mg. Furosemide may increase blood glucose levels, potentially reducing Metformin efficacy. Consider monitoring blood glucose more frequently and adjusting Metformin dosage if A1c rises above target.",
        "evidence_level": "B",
        "confidence": 0.88,
        "source_guideline": "ADA Standards of Care 2024, Section 9",
        "category": "medication_safety",
        "priority": "soon",
        "condition_filter": ["T2DM", "CKD"],
        "feature_importance": [
            {"feature": "Drug Interaction Score", "value": 0.85, "direction": "negative"},
            {"feature": "A1c Level", "value": 0.72, "direction": "negative"},
            {"feature": "eGFR", "value": 0.45, "direction": "negative"},
        ],
    },
    {
        "agent_type": "diagnostic",
        "title": "Overdue A1c Screening",
        "recommendation": "Patient with Type 2 Diabetes has not had an A1c test in the last 90 days. ADA guidelines recommend A1c testing every 3 months for patients not meeting glycemic goals. Schedule A1c lab work at next visit.",
        "evidence_level": "A",
        "confidence": 0.95,
        "source_guideline": "ADA Standards of Care 2024, Section 6",
        "category": "screening",
        "priority": "soon",
        "condition_filter": ["T2DM"],
        "feature_importance": [
            {"feature": "Days Since Last A1c", "value": 0.92, "direction": "negative"},
            {"feature": "Last A1c Value", "value": 0.65, "direction": "negative"},
        ],
    },
    {
        "agent_type": "care_plan",
        "title": "Blood Pressure Above ACC/AHA Target",
        "recommendation": "Patient's average systolic BP over last 3 readings is 152 mmHg, exceeding the ACC/AHA target of <130 mmHg. Consider uptitrating Lisinopril from 10mg to 20mg or adding a second antihypertensive agent. Recheck BP in 4 weeks.",
        "evidence_level": "A",
        "confidence": 0.91,
        "source_guideline": "ACC/AHA 2023 Hypertension Guidelines",
        "category": "chronic_management",
        "priority": "urgent",
        "condition_filter": ["HTN"],
        "feature_importance": [
            {"feature": "Avg Systolic BP", "value": 0.94, "direction": "negative"},
            {"feature": "Current Medication Dose", "value": 0.60, "direction": "positive"},
            {"feature": "Comorbidity Count", "value": 0.45, "direction": "negative"},
        ],
    },
    {
        "agent_type": "triage",
        "title": "Elevated Heart Failure Biomarker",
        "recommendation": "NT-proBNP level of 2,450 pg/mL significantly exceeds the upper normal limit of 125 pg/mL, suggesting decompensated heart failure. Recommend urgent cardiology consultation, assess fluid status, and consider diuretic adjustment. Monitor daily weights.",
        "evidence_level": "A",
        "confidence": 0.93,
        "source_guideline": "ACC/AHA 2023 Heart Failure Guidelines",
        "category": "urgent_care",
        "priority": "critical",
        "condition_filter": ["HF"],
        "feature_importance": [
            {"feature": "NT-proBNP Level", "value": 0.96, "direction": "negative"},
            {"feature": "Weight Change (7d)", "value": 0.72, "direction": "negative"},
            {"feature": "Ejection Fraction", "value": 0.55, "direction": "negative"},
        ],
    },
    {
        "agent_type": "diagnostic",
        "title": "Declining Kidney Function — KDIGO Stage Progression Risk",
        "recommendation": "eGFR has declined from 48 to 38 mL/min/1.73m2 over the past 6 months, representing a >25% decline. Per KDIGO 2024 guidelines, refer to nephrology, check for reversible causes, and ensure ACE inhibitor/ARB is at maximum tolerated dose.",
        "evidence_level": "A",
        "confidence": 0.89,
        "source_guideline": "KDIGO 2024 CKD Guidelines",
        "category": "chronic_management",
        "priority": "urgent",
        "condition_filter": ["CKD"],
        "feature_importance": [
            {"feature": "eGFR Decline Rate", "value": 0.91, "direction": "negative"},
            {"feature": "Creatinine Trend", "value": 0.78, "direction": "negative"},
            {"feature": "Proteinuria", "value": 0.62, "direction": "negative"},
        ],
    },
    {
        "agent_type": "medication",
        "title": "NSAID Contraindication with CKD and Heart Failure",
        "recommendation": "Patient has CKD Stage 3 and Heart Failure. NSAIDs are contraindicated due to risk of acute kidney injury and fluid retention. If prescribed for pain, recommend switching to acetaminophen (max 2g/day given CKD) or topical analgesics.",
        "evidence_level": "A",
        "confidence": 0.96,
        "source_guideline": "KDIGO 2024 / ACC/AHA 2023",
        "category": "medication_safety",
        "priority": "critical",
        "condition_filter": ["CKD", "HF"],
        "feature_importance": [
            {"feature": "CKD Stage", "value": 0.88, "direction": "negative"},
            {"feature": "Heart Failure Status", "value": 0.85, "direction": "negative"},
            {"feature": "Current NSAID Use", "value": 0.92, "direction": "negative"},
        ],
    },
    {
        "agent_type": "care_plan",
        "title": "Atrial Fibrillation Stroke Risk — CHA2DS2-VASc Assessment",
        "recommendation": "Patient with AFib has CHA2DS2-VASc score of 4 (HTN, age, diabetes). Current anticoagulation with Apixaban 5mg BID is appropriate. Recommend annual renal function monitoring to ensure dose remains correct, and assess bleeding risk with HAS-BLED score.",
        "evidence_level": "A",
        "confidence": 0.87,
        "source_guideline": "ACC/AHA 2023 AFib Guidelines",
        "category": "chronic_management",
        "priority": "routine",
        "condition_filter": ["AFib"],
        "feature_importance": [
            {"feature": "CHA2DS2-VASc Score", "value": 0.90, "direction": "negative"},
            {"feature": "Current Anticoagulation", "value": 0.75, "direction": "positive"},
            {"feature": "Renal Function", "value": 0.60, "direction": "negative"},
        ],
    },
    {
        "agent_type": "triage",
        "title": "COPD Exacerbation Risk — Declining O2 Saturation",
        "recommendation": "O2 saturation trending downward: 94% -> 91% -> 89% over last 3 readings. Patient is at risk for acute COPD exacerbation. Consider short course of oral corticosteroids (prednisone 40mg x 5 days per GOLD 2024), increase bronchodilator frequency, and schedule pulmonology follow-up.",
        "evidence_level": "A",
        "confidence": 0.90,
        "source_guideline": "GOLD 2024 COPD Guidelines",
        "category": "urgent_care",
        "priority": "urgent",
        "condition_filter": ["COPD"],
        "feature_importance": [
            {"feature": "O2 Saturation Trend", "value": 0.93, "direction": "negative"},
            {"feature": "Exacerbation History", "value": 0.70, "direction": "negative"},
            {"feature": "Current Inhaler Compliance", "value": 0.55, "direction": "positive"},
        ],
    },
    {
        "agent_type": "diagnostic",
        "title": "Coronary Artery Disease — LDL Above Target",
        "recommendation": "LDL cholesterol is 145 mg/dL, well above the <70 mg/dL target for patients with established CAD. Consider increasing Atorvastatin from 40mg to 80mg daily, or adding Ezetimibe 10mg if already on maximum statin dose. Recheck lipids in 6-8 weeks.",
        "evidence_level": "A",
        "confidence": 0.92,
        "source_guideline": "ACC/AHA 2023 Cholesterol Guidelines",
        "category": "chronic_management",
        "priority": "soon",
        "condition_filter": ["CAD"],
        "feature_importance": [
            {"feature": "LDL Level", "value": 0.95, "direction": "negative"},
            {"feature": "Current Statin Dose", "value": 0.68, "direction": "positive"},
            {"feature": "ASCVD Risk Score", "value": 0.80, "direction": "negative"},
        ],
    },
    {
        "agent_type": "care_plan",
        "title": "Diabetes Self-Management Education Referral",
        "recommendation": "Patient with poorly controlled T2DM (A1c 9.2%) has not completed Diabetes Self-Management Education (DSME). Studies show DSME reduces A1c by 0.5-1.0%. Recommend referral to certified diabetes educator and nutritional counseling.",
        "evidence_level": "B",
        "confidence": 0.84,
        "source_guideline": "ADA Standards of Care 2024, Section 5",
        "category": "patient_education",
        "priority": "routine",
        "condition_filter": ["T2DM"],
        "feature_importance": [
            {"feature": "A1c Level", "value": 0.82, "direction": "negative"},
            {"feature": "DSME Completion", "value": 0.90, "direction": "positive"},
            {"feature": "Medication Adherence", "value": 0.65, "direction": "positive"},
        ],
    },
]

# Mapping from MRN to conditions for matching recommendations to patients
PATIENT_CONDITIONS = {
    "MRN001": ["T2DM", "HTN", "CKD"],
    "MRN002": ["HTN", "HF"],
    "MRN003": ["T2DM", "CAD"],
    "MRN004": ["T2DM", "HTN", "COPD"],
    "MRN005": ["CAD", "HF", "AFib"],
}


def seed_recommendations_json(output_file: Optional[str] = None) -> list[dict]:
    """
    Generate recommendation seed data as JSON.
    Can be loaded via the API or directly into the database.
    """
    import random
    random.seed(99)

    seeded = []
    now = datetime.now(timezone.utc)

    for rec in RECOMMENDATIONS:
        required_conditions = set(rec["condition_filter"])

        matching_mrns = []
        for mrn, conds in PATIENT_CONDITIONS.items():
            if required_conditions.issubset(set(conds)):
                matching_mrns.append(mrn)

        if not matching_mrns:
            logger.info(f"SKIP: No matching patients for '{rec['title']}'")
            continue

        for mrn in matching_mrns[:2]:
            hours_ago = random.randint(1, 72)
            created_time = now - timedelta(hours=hours_ago)

            entry = {
                "id": str(uuid.uuid4()),
                "patient_mrn": mrn,
                "agent_type": rec["agent_type"],
                "action_type": "recommendation",
                "title": rec["title"],
                "recommendation": rec["recommendation"],
                "evidence_level": rec["evidence_level"],
                "confidence": rec["confidence"],
                "source_guideline": rec["source_guideline"],
                "category": rec["category"],
                "priority": rec["priority"],
                "feature_importance": rec.get("feature_importance", []),
                "conditions": list(PATIENT_CONDITIONS.get(mrn, [])),
                "created_at": created_time.isoformat(),
                "trigger_source": "seed_script",
            }
            seeded.append(entry)

    logger.info(f"Generated {len(seeded)} AI recommendations")

    # Breakdown
    for agent_type in ["triage", "medication", "diagnostic", "care_plan"]:
        count = sum(1 for r in seeded if r["agent_type"] == agent_type)
        logger.info(f"  {agent_type}: {count} recommendations")

    if output_file:
        with open(output_file, "w") as f:
            json.dump(seeded, f, indent=2, default=str)
        logger.info(f"Saved to {output_file}")

    return seeded


def seed_via_api(api_url: str, token: Optional[str] = None) -> bool:
    """POST recommendations to the HealthOS API."""
    recommendations = seed_recommendations_json()

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    endpoint = f"{api_url.rstrip('/')}/api/v1/agents/recommendations/seed"

    try:
        resp = requests.post(endpoint, json=recommendations, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            logger.info(f"Seeded {len(recommendations)} recommendations via API (HTTP {resp.status_code})")
            return True
        else:
            logger.warning(f"API returned HTTP {resp.status_code}: {resp.text[:200]}")
            logger.info("Falling back to JSON output...")
            seed_recommendations_json(output_file=str(PROJECT_DIR / "data" / "seed_recommendations.json"))
            return False
    except requests.RequestException as exc:
        logger.warning(f"API not reachable: {exc}")
        logger.info("Falling back to JSON output...")
        os.makedirs(PROJECT_DIR / "data", exist_ok=True)
        seed_recommendations_json(output_file=str(PROJECT_DIR / "data" / "seed_recommendations.json"))
        return False


def main():
    parser = argparse.ArgumentParser(description="Seed HealthOS with sample AI recommendations")
    parser.add_argument("--api-url", default=API_BASE_URL, help="HealthOS API base URL")
    parser.add_argument("--token", default=None, help="JWT bearer token")
    parser.add_argument("--json-only", action="store_true", help="Output JSON file only (no API call)")
    parser.add_argument("--output", default=None, help="Output JSON file path")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Eminence HealthOS - AI Recommendations Seed Script")
    logger.info("=" * 60)

    if args.json_only:
        output = args.output or str(PROJECT_DIR / "data" / "seed_recommendations.json")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        seed_recommendations_json(output_file=output)
    else:
        seed_via_api(api_url=args.api_url, token=args.token)


if __name__ == "__main__":
    main()
