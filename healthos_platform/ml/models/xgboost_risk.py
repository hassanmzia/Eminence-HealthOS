"""
XGBoost 7-day hospitalization risk scoring model.
Predicts probability of hospitalization/ED visit within 7 days.

Adapted for HealthOS (FastAPI + SQLAlchemy). Django ORM references replaced
with plain-dict patient data interface.
"""

import logging
from datetime import datetime, timedelta, timezone as tz
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.xgboost_risk")


class XGBoostRiskModel:
    """
    XGBoost model for 7-day hospitalization risk prediction.

    Features: clinical labs, vitals, demographics, utilization history, medications.
    Output: probability score 0.0 - 1.0

    ``patient_data`` should be a plain dict with observations, conditions,
    medication_requests, encounters, etc.
    """

    # Feature names in order (must match training)
    FEATURE_NAMES = [
        # Demographics
        "age", "gender_encoded", "num_chronic_conditions",
        # Lab values
        "a1c_latest", "a1c_trend_90d", "glucose_latest", "glucose_avg_7d", "glucose_variability",
        "bp_systolic_latest", "bp_diastolic_latest", "bp_avg_30d",
        "creatinine_latest", "egfr_latest", "bun_latest",
        "wbc_latest", "hemoglobin_latest", "potassium_latest",
        "bnp_latest", "troponin_latest",
        # Medications
        "num_active_medications", "num_high_risk_medications", "medication_adherence_score",
        # Utilization
        "ed_visits_90d", "hospitalizations_180d", "readmission_30d_flag",
        # Vitals trends
        "weight_change_kg_30d", "heart_rate_avg_7d", "spo2_avg_7d",
        # Social
        "sdoh_risk_score", "engagement_score",
        # Care gaps
        "num_open_care_gaps", "days_since_last_visit",
    ]

    def __init__(self, model_path: str = None):
        self.model = None
        self.model_path = model_path
        self.version = "xgboost_7day_v2"
        self._is_loaded = False

    def load(self):
        """Load trained XGBoost model from disk."""
        import xgboost as xgb
        try:
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=10,
                eval_metric="auc",
                use_label_encoder=False,
            )
            if self.model_path:
                self.model.load_model(self.model_path)
                logger.info(f"XGBoost model loaded from {self.model_path}")
            self._is_loaded = True
        except Exception as e:
            logger.error(f"XGBoost model load failed: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_obs_values(
        patient_data: Dict[str, Any],
        code: str,
        *,
        since: Optional[datetime] = None,
        status: str = "final",
    ) -> List[float]:
        """Return list of observation values matching code/since/status."""
        obs_list = patient_data.get("observations", [])
        results = []
        for o in obs_list:
            if o.get("code") != code:
                continue
            if status and o.get("status") != status:
                continue
            if since and o.get("effective_datetime") and o["effective_datetime"] < since:
                continue
            if o.get("value") is not None:
                results.append(float(o["value"]))
        return results

    @staticmethod
    def _latest_obs(
        patient_data: Dict[str, Any],
        code: str,
        *,
        since: Optional[datetime] = None,
        status: str = "final",
    ) -> Optional[float]:
        obs_list = patient_data.get("observations", [])
        candidates = []
        for o in obs_list:
            if o.get("code") != code:
                continue
            if status and o.get("status") != status:
                continue
            if since and o.get("effective_datetime") and o["effective_datetime"] < since:
                continue
            if o.get("value") is not None:
                candidates.append(o)
        if not candidates:
            return None
        candidates.sort(key=lambda o: o.get("effective_datetime", datetime.min), reverse=True)
        return float(candidates[0]["value"])

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def extract_features(self, patient_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract feature values from a patient data dict.

        Expected ``patient_data`` layout::

            {
                "age": 65,
                "gender": "male",
                "observations": [...],
                "conditions": [...],
                "medication_requests": [...],
                "encounters": [...],
                "sdoh_assessments": [...],
                "care_gaps": [...],
                "engagement_score": 50,
            }

        Returns dict with feature_name -> value.
        """
        features: Dict[str, float] = {}
        now = datetime.now(tz=tz.utc)

        # Demographics
        features["age"] = patient_data.get("age") or 0
        features["gender_encoded"] = 1 if patient_data.get("gender") == "male" else 0
        conditions = [c for c in patient_data.get("conditions", []) if c.get("clinical_status") == "active"]
        features["num_chronic_conditions"] = len(conditions)

        # Lab values
        features["a1c_latest"] = self._latest_obs(patient_data, "4548-4", since=now - timedelta(days=90)) or 0
        features["glucose_latest"] = self._latest_obs(patient_data, "2339-0", since=now - timedelta(days=7)) or 100

        glucose_7d = self._get_obs_values(patient_data, "2339-0", since=now - timedelta(days=7))
        features["glucose_variability"] = float(np.std(glucose_7d)) if len(glucose_7d) >= 3 else 0
        features["glucose_avg_7d"] = float(np.mean(glucose_7d)) if glucose_7d else 100

        # A1C trend
        old_a1c_vals = self._get_obs_values(
            patient_data, "4548-4",
            since=now - timedelta(days=180),
        )
        # Rough approximation: latest minus oldest in the window
        current_a1c = features["a1c_latest"]
        if len(old_a1c_vals) >= 2:
            features["a1c_trend_90d"] = old_a1c_vals[-1] - old_a1c_vals[0]
        else:
            features["a1c_trend_90d"] = 0

        # Blood pressure
        features["bp_systolic_latest"] = self._latest_obs(patient_data, "8480-6") or 120
        features["bp_diastolic_latest"] = self._latest_obs(patient_data, "8462-4") or 80
        features["bp_avg_30d"] = features["bp_systolic_latest"]

        # Kidney function
        features["creatinine_latest"] = self._latest_obs(patient_data, "2160-0") or 1.0
        features["egfr_latest"] = self._latest_obs(patient_data, "48642-3") or 60
        features["bun_latest"] = self._latest_obs(patient_data, "3094-0") or 15

        # CBC
        features["wbc_latest"] = self._latest_obs(patient_data, "6690-2") or 7.0
        features["hemoglobin_latest"] = self._latest_obs(patient_data, "718-7") or 13.0
        features["potassium_latest"] = self._latest_obs(patient_data, "2823-3") or 4.0

        # Cardiac
        features["bnp_latest"] = self._latest_obs(patient_data, "42637-9") or 0
        features["troponin_latest"] = self._latest_obs(patient_data, "6598-7") or 0

        # Medications
        med_requests = patient_data.get("medication_requests", [])
        active_meds = [m for m in med_requests if m.get("status") == "active"]
        features["num_active_medications"] = len(active_meds)
        features["num_high_risk_medications"] = 0  # TODO: check against high-risk drug list
        features["medication_adherence_score"] = 0.8

        # Utilization
        encounters = patient_data.get("encounters", [])
        cutoff_90d = now - timedelta(days=90)
        cutoff_180d = now - timedelta(days=180)
        cutoff_30d = now - timedelta(days=30)

        features["ed_visits_90d"] = sum(
            1 for e in encounters
            if e.get("encounter_class") == "EMER"
            and e.get("period_start") and e["period_start"] >= cutoff_90d
        )
        features["hospitalizations_180d"] = sum(
            1 for e in encounters
            if e.get("encounter_class") == "IMP"
            and e.get("period_start") and e["period_start"] >= cutoff_180d
        )
        recent_inpatient = sum(
            1 for e in encounters
            if e.get("encounter_class") == "IMP"
            and e.get("period_start") and e["period_start"] >= cutoff_30d
        )
        features["readmission_30d_flag"] = 1 if recent_inpatient >= 2 else 0

        # Vitals
        features["weight_change_kg_30d"] = 0
        features["heart_rate_avg_7d"] = self._latest_obs(patient_data, "8867-4") or 72
        features["spo2_avg_7d"] = self._latest_obs(patient_data, "59408-5") or 98

        # SDOH
        sdoh_assessments = patient_data.get("sdoh_assessments", [])
        if sdoh_assessments:
            features["sdoh_risk_score"] = sdoh_assessments[-1].get("total_score", 0)
        else:
            features["sdoh_risk_score"] = 0

        # Engagement
        features["engagement_score"] = patient_data.get("engagement_score", 50)

        # Care gaps
        care_gaps = patient_data.get("care_gaps", [])
        features["num_open_care_gaps"] = sum(
            1 for g in care_gaps if g.get("status") == "open"
        )

        # Days since last visit
        if encounters:
            sorted_enc = sorted(encounters, key=lambda e: e.get("period_start", datetime.min), reverse=True)
            last_start = sorted_enc[0].get("period_start")
            if last_start:
                features["days_since_last_visit"] = (now - last_start).days
            else:
                features["days_since_last_visit"] = 365
        else:
            features["days_since_last_visit"] = 365

        return features

    def predict(self, features: Dict[str, float]) -> float:
        """
        Predict 7-day hospitalization risk.
        Returns probability score 0.0 - 1.0.
        """
        if not self._is_loaded:
            self.load()

        feature_vector = np.array([
            features.get(name, 0.0) for name in self.FEATURE_NAMES
        ]).reshape(1, -1)

        if self.model is None:
            return self._heuristic_score(features)

        try:
            proba = self.model.predict_proba(feature_vector)[0][1]
            return float(proba)
        except Exception as e:
            logger.error(f"XGBoost prediction failed: {e}")
            return self._heuristic_score(features)

    def _heuristic_score(self, features: Dict[str, float]) -> float:
        """Simple heuristic risk score when ML model is unavailable."""
        score = 0.1

        a1c = features.get("a1c_latest", 0)
        if a1c > 10:
            score += 0.25
        elif a1c > 8:
            score += 0.10

        if features.get("bp_systolic_latest", 120) > 160:
            score += 0.15

        score += features.get("ed_visits_90d", 0) * 0.10
        score += features.get("hospitalizations_180d", 0) * 0.15
        score += features.get("readmission_30d_flag", 0) * 0.20

        score += min(0.20, features.get("num_chronic_conditions", 0) * 0.04)
        score += min(0.10, features.get("num_open_care_gaps", 0) * 0.02)

        return min(1.0, score)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return feature importances from the trained model."""
        if self.model is None or not self._is_loaded:
            return {}
        try:
            importances = self.model.feature_importances_
            return dict(sorted(
                zip(self.FEATURE_NAMES, importances.tolist()),
                key=lambda x: x[1],
                reverse=True,
            ))
        except Exception:
            return {}
