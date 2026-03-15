"""
Multi-modal attention fusion model for comprehensive patient risk assessment.
Fuses structured EHR data, time-series vitals, clinical notes embeddings,
and social determinants of health (SDOH) into a unified risk score.

Adapted for HealthOS (FastAPI + SQLAlchemy). Django ORM references replaced
with plain-dict patient data interface.
"""

import logging
from datetime import datetime, timedelta, timezone as tz
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.multimodal_risk")

# Modality dimensions
EHR_STRUCTURED_DIM = 64
TIMESERIES_DIM = 32
NOTES_EMBEDDING_DIM = 768
SDOH_DIM = 16
FUSION_DIM = 128
N_ATTENTION_HEADS = 4


class MultiModalAttentionFusion:
    """
    Multi-modal attention fusion model for patient risk assessment.

    Architecture:
        1. Modality-specific encoders (EHR, TimeSeries, Notes, SDOH)
        2. Cross-modal attention (each modality attends to all others)
        3. Fusion MLP for final risk score

    Supports inference even with missing modalities via masking.

    ``patient_data`` should be a plain dict with observations, conditions,
    medication_requests, encounters, document_references, sdoh_assessments, etc.
    """

    def __init__(self, model_path: str = None):
        self.model = None
        self.model_path = model_path
        self.version = "multimodal_v1"
        self._is_loaded = False

    def build_model(self):
        """Build the multi-modal fusion model using PyTorch."""
        try:
            import torch
            import torch.nn as nn

            class ModalityEncoder(nn.Module):
                """Per-modality encoder projecting to FUSION_DIM."""

                def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(input_dim, hidden_dim),
                        nn.LayerNorm(hidden_dim),
                        nn.GELU(),
                        nn.Dropout(0.1),
                        nn.Linear(hidden_dim, output_dim),
                    )

                def forward(self, x):
                    return self.net(x)

            class CrossModalAttention(nn.Module):
                """Multi-head cross-modal attention."""

                def __init__(self, embed_dim: int, num_heads: int):
                    super().__init__()
                    self.attn = nn.MultiheadAttention(
                        embed_dim=embed_dim,
                        num_heads=num_heads,
                        dropout=0.1,
                        batch_first=True,
                    )
                    self.norm = nn.LayerNorm(embed_dim)

                def forward(self, query, key_value, key_padding_mask=None):
                    out, weights = self.attn(
                        query, key_value, key_value,
                        key_padding_mask=key_padding_mask,
                    )
                    return self.norm(query + out), weights

            class MultiModalRiskModel(nn.Module):
                """Full multi-modal fusion model."""

                def __init__(self):
                    super().__init__()
                    self.ehr_encoder = ModalityEncoder(EHR_STRUCTURED_DIM, 128, FUSION_DIM)
                    self.ts_encoder = ModalityEncoder(TIMESERIES_DIM, 64, FUSION_DIM)
                    self.notes_encoder = ModalityEncoder(NOTES_EMBEDDING_DIM, 256, FUSION_DIM)
                    self.sdoh_encoder = ModalityEncoder(SDOH_DIM, 32, FUSION_DIM)

                    self.ehr_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)
                    self.ts_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)
                    self.notes_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)
                    self.sdoh_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)

                    self.fusion = nn.Sequential(
                        nn.Linear(FUSION_DIM * 4, 256),
                        nn.LayerNorm(256),
                        nn.GELU(),
                        nn.Dropout(0.2),
                        nn.Linear(256, 64),
                        nn.GELU(),
                        nn.Linear(64, 1),
                        nn.Sigmoid(),
                    )

                    self.modality_weights = nn.Parameter(
                        torch.ones(4) / 4
                    )

                def forward(
                    self,
                    ehr_features,
                    ts_features,
                    notes_features,
                    sdoh_features,
                    modality_mask=None,
                ):
                    e_ehr = self.ehr_encoder(ehr_features).unsqueeze(1)
                    e_ts = self.ts_encoder(ts_features).unsqueeze(1)
                    e_notes = self.notes_encoder(notes_features).unsqueeze(1)
                    e_sdoh = self.sdoh_encoder(sdoh_features).unsqueeze(1)

                    all_modalities = torch.cat([e_ehr, e_ts, e_notes, e_sdoh], dim=1)

                    e_ehr_fused, _ = self.ehr_attn(e_ehr, all_modalities)
                    e_ts_fused, _ = self.ts_attn(e_ts, all_modalities)
                    e_notes_fused, _ = self.notes_attn(e_notes, all_modalities)
                    e_sdoh_fused, _ = self.sdoh_attn(e_sdoh, all_modalities)

                    weights = torch.softmax(self.modality_weights, dim=0)
                    e_ehr_fused = e_ehr_fused * weights[0]
                    e_ts_fused = e_ts_fused * weights[1]
                    e_notes_fused = e_notes_fused * weights[2]
                    e_sdoh_fused = e_sdoh_fused * weights[3]

                    if modality_mask is not None:
                        for i, emb in enumerate([e_ehr_fused, e_ts_fused, e_notes_fused, e_sdoh_fused]):
                            emb[modality_mask[:, i]] = 0.0

                    fused = torch.cat([
                        e_ehr_fused.squeeze(1),
                        e_ts_fused.squeeze(1),
                        e_notes_fused.squeeze(1),
                        e_sdoh_fused.squeeze(1),
                    ], dim=-1)

                    return self.fusion(fused)

            return MultiModalRiskModel()

        except ImportError:
            logger.warning("PyTorch not available. Using heuristic fusion.")
            return None

    def load(self):
        """Load or initialize the multi-modal model."""
        import os

        if self.model_path and os.path.exists(self.model_path):
            try:
                import torch
                self.model = self.build_model()
                if self.model is not None:
                    state_dict = torch.load(self.model_path, map_location="cpu")
                    self.model.load_state_dict(state_dict)
                    self.model.eval()
                    logger.info(f"Multi-modal model loaded from {self.model_path}")
                    self._is_loaded = True
                    return
            except Exception as e:
                logger.warning(f"Could not load multi-modal model: {e}")

        self.model = self.build_model()
        if self.model is not None:
            self.model.eval()
        self._is_loaded = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_obs_values(
        patient_data: Dict[str, Any],
        code: str,
        *,
        since: Optional[datetime] = None,
    ) -> List[float]:
        obs_list = patient_data.get("observations", [])
        results = []
        for o in obs_list:
            if o.get("code") != code:
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
    ) -> Optional[float]:
        obs_list = patient_data.get("observations", [])
        candidates = [
            o for o in obs_list
            if o.get("code") == code
            and (since is None or (o.get("effective_datetime") and o["effective_datetime"] >= since))
            and o.get("value") is not None
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda o: o.get("effective_datetime", datetime.min), reverse=True)
        return float(candidates[0]["value"])

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def extract_ehr_features(self, patient_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract structured EHR features.

        Features: demographics (4) + recent labs (30) + condition flags (20) + utilization (10)
        Total: 64 features
        """
        features = np.zeros(EHR_STRUCTURED_DIM)
        now = datetime.now(tz=tz.utc)
        cutoff_90d = now - timedelta(days=90)

        # Demographics (indices 0-3)
        age = patient_data.get("age") or 0
        features[0] = min(age / 100.0, 1.0)

        gender = (patient_data.get("gender") or "unknown").lower()
        features[1] = 1.0 if gender in ("male", "m") else 0.0
        features[2] = 1.0 if gender in ("female", "f") else 0.0

        # Recent labs (indices 4-17)
        LAB_CODES = [
            ("4548-4", 4, 14.0),
            ("33914-3", 5, 150.0),
            ("18262-6", 6, 250.0),
            ("2085-9", 7, 100.0),
            ("2160-0", 8, 15.0),
            ("8480-6", 9, 200.0),
            ("8462-4", 10, 120.0),
            ("2951-2", 11, 150.0),
            ("6298-4", 12, 7.0),
            ("718-7", 13, 20.0),
            ("6690-2", 14, 20.0),
            ("777-3", 15, 400.0),
            ("39156-5", 16, 60.0),
            ("2339-0", 17, 400.0),
        ]

        for loinc_code, idx, norm_val in LAB_CODES:
            val = self._latest_obs(patient_data, loinc_code, since=cutoff_90d)
            if val is not None:
                features[idx] = val / norm_val

        # Chronic condition flags (indices 34-53)
        CHRONIC_ICD_PREFIXES = [
            "E11", "I10", "E78", "J44", "I50", "N18", "F32", "F41", "E66", "I25",
            "J45", "M06", "K21", "G47", "E03", "M54", "I48", "N39", "K58", "G43",
        ]
        conditions = patient_data.get("conditions", [])
        for i, prefix in enumerate(CHRONIC_ICD_PREFIXES):
            has_condition = any(
                c.get("code", "").startswith(prefix) and c.get("clinical_status") == "active"
                for c in conditions
            )
            features[34 + i] = 1.0 if has_condition else 0.0

        # Utilization features (indices 54-63)
        encounters = patient_data.get("encounters", [])
        enc_90d = [e for e in encounters if e.get("start_datetime") and e["start_datetime"] >= cutoff_90d]
        features[54] = min(len(enc_90d) / 10.0, 1.0)

        ed_visits = [e for e in enc_90d if e.get("encounter_class") == "emergency"]
        features[55] = min(len(ed_visits) / 5.0, 1.0)

        hosp = [e for e in enc_90d if e.get("encounter_class") == "inpatient"]
        features[56] = min(len(hosp) / 3.0, 1.0)

        med_requests = patient_data.get("medication_requests", [])
        active_meds = [m for m in med_requests if m.get("status") == "active"]
        features[57] = min(len(active_meds) / 20.0, 1.0)

        care_gaps = patient_data.get("care_gaps", [])
        open_gaps = [g for g in care_gaps if g.get("status") == "open"]
        features[58] = min(len(open_gaps) / 10.0, 1.0)

        return features

    def extract_timeseries_features(self, patient_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract time-series encoded features.
        Returns 32-dim encoded representation.
        """
        features = np.zeros(TIMESERIES_DIM)
        now = datetime.now(tz=tz.utc)
        cutoff_7d = now - timedelta(days=7)

        # CGM statistics (indices 0-7)
        glucose_vals = self._get_obs_values(patient_data, "2339-0", since=cutoff_7d)
        if glucose_vals:
            glucose_arr = np.array(glucose_vals)
            features[0] = np.mean(glucose_arr) / 400.0
            features[1] = np.std(glucose_arr) / 100.0
            features[2] = np.min(glucose_arr) / 400.0
            features[3] = np.max(glucose_arr) / 400.0
            features[4] = np.sum(glucose_arr < 70) / max(len(glucose_arr), 1)
            features[5] = np.sum(glucose_arr > 180) / max(len(glucose_arr), 1)
            features[6] = np.sum((glucose_arr >= 70) & (glucose_arr <= 180)) / max(len(glucose_arr), 1)
            features[7] = (np.std(glucose_arr) / np.mean(glucose_arr)) if np.mean(glucose_arr) > 0 else 0

        # BP statistics (indices 8-11)
        systolic_vals = self._get_obs_values(patient_data, "8480-6", since=cutoff_7d)
        if systolic_vals:
            sys_arr = np.array(systolic_vals)
            features[8] = np.mean(sys_arr) / 200.0
            features[9] = np.std(sys_arr) / 50.0
            features[10] = np.sum(sys_arr > 140) / max(len(sys_arr), 1)
            features[11] = np.sum(sys_arr < 90) / max(len(sys_arr), 1)

        # Heart rate statistics (indices 12-15)
        hr_vals = self._get_obs_values(patient_data, "8867-4", since=cutoff_7d)
        if hr_vals:
            hr_arr = np.array(hr_vals)
            features[12] = np.mean(hr_arr) / 200.0
            features[13] = np.std(hr_arr) / 50.0
            features[14] = np.sum(hr_arr > 100) / max(len(hr_arr), 1)
            features[15] = np.sum(hr_arr < 60) / max(len(hr_arr), 1)

        # Activity / steps statistics (indices 16-19)
        steps_vals = self._get_obs_values(patient_data, "55423-8", since=cutoff_7d)
        if steps_vals:
            steps_arr = np.array(steps_vals)
            features[16] = np.mean(steps_arr) / 10000.0
            features[17] = np.min(steps_arr) / 10000.0
            features[18] = np.sum(steps_arr < 2000) / max(len(steps_arr), 1)
            features[19] = np.sum(steps_arr > 8000) / max(len(steps_arr), 1)

        # Weight trend (indices 20-23)
        weight_vals = self._get_obs_values(patient_data, "29463-7", since=now - timedelta(days=30))
        if len(weight_vals) >= 2:
            weight_arr = np.array(weight_vals)
            weight_change = weight_arr[-1] - weight_arr[0]
            features[20] = weight_arr[-1] / 200.0
            features[21] = weight_change / 20.0
            features[22] = 1.0 if weight_change > 2.0 else 0.0
            features[23] = 1.0 if weight_change < -2.0 else 0.0

        # SpO2 statistics (indices 24-25)
        spo2_vals = self._get_obs_values(patient_data, "59408-5", since=cutoff_7d)
        if spo2_vals:
            spo2_arr = np.array(spo2_vals)
            features[24] = np.mean(spo2_arr) / 100.0
            features[25] = np.sum(spo2_arr < 92) / max(len(spo2_arr), 1)

        # Observation data density (indices 28-31)
        all_obs = patient_data.get("observations", [])
        obs_7d = [o for o in all_obs if o.get("effective_datetime") and o["effective_datetime"] >= cutoff_7d]
        features[28] = min(len(obs_7d) / 100.0, 1.0)
        features[29] = min(len(glucose_vals) / 288.0, 1.0)
        features[30] = min(len(systolic_vals) / 14.0, 1.0)
        features[31] = min(len(steps_vals) / 7.0, 1.0)

        return features

    def extract_notes_features(self, patient_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract clinical notes embedding using sentence transformers.
        Returns 768-dim embedding of recent clinical notes.
        """
        cutoff_90d = datetime.now(tz=tz.utc) - timedelta(days=90)

        doc_refs = patient_data.get("document_references", [])
        recent_notes = [
            d for d in doc_refs
            if d.get("status") == "current"
            and d.get("date") is not None
            and d["date"] >= cutoff_90d
        ]
        recent_notes.sort(key=lambda d: d["date"], reverse=True)
        note_texts = [d["description"] for d in recent_notes[:5] if d.get("description")]

        if not note_texts:
            return np.zeros(NOTES_EMBEDDING_DIM)

        combined_text = " ".join(note_texts)[:2000]

        try:
            # Try project-local embedding utility first
            from healthos_platform.ml.rag.embeddings import generate_embedding  # type: ignore
            embedding = generate_embedding(combined_text)
            if embedding is not None:
                return np.array(embedding)
        except Exception as e:
            logger.debug(f"Could not generate notes embedding: {e}")

        return np.zeros(NOTES_EMBEDDING_DIM)

    def extract_sdoh_features(self, patient_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract SDOH features from patient data.
        Returns 16-dim SDOH feature vector.
        """
        features = np.zeros(SDOH_DIM)

        try:
            assessments = patient_data.get("sdoh_assessments", [])
            if not assessments:
                return features

            # Use most recent assessment
            assessment = sorted(
                assessments,
                key=lambda a: a.get("assessment_date", datetime.min),
                reverse=True,
            )[0]

            features[0] = (assessment.get("housing_instability_score") or 0) / 4.0
            features[1] = (assessment.get("food_insecurity_score") or 0) / 4.0
            features[2] = (assessment.get("transportation_score") or 0) / 4.0
            features[3] = (assessment.get("social_isolation_score") or 0) / 4.0
            features[4] = (assessment.get("financial_strain_score") or 0) / 4.0
            features[5] = 1.0 if assessment.get("education_less_than_high_school") else 0.0
            features[6] = 1.0 if assessment.get("unemployed") else 0.0
            features[7] = 1.0 if assessment.get("domestic_violence_risk") else 0.0
            features[8] = 1.0 if assessment.get("substance_use_concern") else 0.0
            features[9] = 1.0 if assessment.get("mental_health_concern") else 0.0
            features[10] = (assessment.get("total_score") or 0) / 20.0

            risk = assessment.get("overall_sdoh_risk") or "low"
            features[11] = 1.0 if risk == "low" else 0.0
            features[12] = 1.0 if risk == "medium" else 0.0
            features[13] = 1.0 if risk == "high" else 0.0
            features[14] = 1.0 if risk == "critical" else 0.0

            features[15] = 1.0  # Assessment available flag
        except Exception as e:
            logger.debug(f"Could not extract SDOH features: {e}")

        return features

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        patient_data: Dict[str, Any],
        return_modality_contributions: bool = False,
    ) -> Dict:
        """
        Run multi-modal risk prediction for a patient.

        Args:
            patient_data: Patient data dict
            return_modality_contributions: If True, include per-modality risk contributions

        Returns:
            {
                risk_score: float (0-1),
                risk_level: str (low/moderate/high/critical),
                confidence: float (0-1),
                modality_contributions: dict (optional),
                missing_modalities: list,
            }
        """
        if not self._is_loaded:
            self.load()

        missing_modalities: List[str] = []

        ehr_features = self.extract_ehr_features(patient_data)
        ts_features = self.extract_timeseries_features(patient_data)
        notes_features = self.extract_notes_features(patient_data)
        sdoh_features = self.extract_sdoh_features(patient_data)

        if np.all(ts_features == 0):
            missing_modalities.append("timeseries")
        if np.all(notes_features == 0):
            missing_modalities.append("clinical_notes")
        if sdoh_features[15] == 0:
            missing_modalities.append("sdoh")

        confidence = 1.0 - (len(missing_modalities) * 0.15)

        if self.model is not None:
            try:
                import torch

                modality_mask = torch.zeros(1, 4, dtype=torch.bool)
                if "timeseries" in missing_modalities:
                    modality_mask[0, 1] = True
                if "clinical_notes" in missing_modalities:
                    modality_mask[0, 2] = True
                if "sdoh" in missing_modalities:
                    modality_mask[0, 3] = True

                with torch.no_grad():
                    risk_tensor = self.model(
                        torch.tensor(ehr_features, dtype=torch.float32).unsqueeze(0),
                        torch.tensor(ts_features, dtype=torch.float32).unsqueeze(0),
                        torch.tensor(notes_features, dtype=torch.float32).unsqueeze(0),
                        torch.tensor(sdoh_features, dtype=torch.float32).unsqueeze(0),
                        modality_mask,
                    )
                    risk_score = float(risk_tensor.item())

                result: Dict[str, Any] = {
                    "risk_score": risk_score,
                    "risk_level": self._categorize_risk(risk_score),
                    "confidence": confidence,
                    "missing_modalities": missing_modalities,
                    "model": "multimodal_attention_fusion",
                }

                if return_modality_contributions:
                    result["modality_contributions"] = self._compute_modality_contributions(
                        ehr_features, ts_features, notes_features, sdoh_features
                    )

                return result

            except Exception as e:
                logger.warning(f"Multi-modal model inference failed: {e}")

        return self._heuristic_fusion(
            ehr_features, ts_features, sdoh_features,
            missing_modalities, confidence,
        )

    def _heuristic_fusion(
        self,
        ehr_features: np.ndarray,
        ts_features: np.ndarray,
        sdoh_features: np.ndarray,
        missing_modalities: List[str],
        confidence: float,
    ) -> Dict:
        """Heuristic multi-modal fusion when neural model unavailable."""
        chronic_flags = ehr_features[34:54]
        ehr_score = (
            np.mean(chronic_flags) * 0.5 +
            ehr_features[55] * 0.25 +
            ehr_features[56] * 0.25
        )

        ts_score = (
            ts_features[1] * 0.3 +
            ts_features[4] * 0.3 +
            ts_features[10] * 0.25 +
            ts_features[18] * 0.15
        ) if "timeseries" not in missing_modalities else ehr_score * 0.5

        sdoh_score = sdoh_features[10] if "sdoh" not in missing_modalities else 0.3

        weights = {"ehr": 0.50, "timeseries": 0.30, "sdoh": 0.20}
        risk_score = (
            ehr_score * weights["ehr"] +
            ts_score * weights["timeseries"] +
            sdoh_score * weights["sdoh"]
        )
        risk_score = float(np.clip(risk_score, 0.0, 1.0))

        return {
            "risk_score": risk_score,
            "risk_level": self._categorize_risk(risk_score),
            "confidence": confidence,
            "missing_modalities": missing_modalities,
            "model": "heuristic_fusion",
        }

    def _compute_modality_contributions(
        self,
        ehr_features: np.ndarray,
        ts_features: np.ndarray,
        notes_features: np.ndarray,
        sdoh_features: np.ndarray,
    ) -> Dict[str, float]:
        """Compute approximate per-modality contribution via ablation."""
        contributions: Dict[str, float] = {}
        try:
            import torch

            def _score_with_zeroed(zero_idx: int) -> float:
                inputs = [
                    torch.tensor(ehr_features, dtype=torch.float32).unsqueeze(0),
                    torch.tensor(ts_features, dtype=torch.float32).unsqueeze(0),
                    torch.tensor(notes_features, dtype=torch.float32).unsqueeze(0),
                    torch.tensor(sdoh_features, dtype=torch.float32).unsqueeze(0),
                ]
                mask = torch.zeros(1, 4, dtype=torch.bool)
                mask[0, zero_idx] = True
                with torch.no_grad():
                    return float(self.model(*inputs, mask).item())

            full_score_tensor = self.model(
                torch.tensor(ehr_features, dtype=torch.float32).unsqueeze(0),
                torch.tensor(ts_features, dtype=torch.float32).unsqueeze(0),
                torch.tensor(notes_features, dtype=torch.float32).unsqueeze(0),
                torch.tensor(sdoh_features, dtype=torch.float32).unsqueeze(0),
                torch.zeros(1, 4, dtype=torch.bool),
            )
            full_score = float(full_score_tensor.item())

            contributions["ehr_structured"] = abs(full_score - _score_with_zeroed(0))
            contributions["timeseries"] = abs(full_score - _score_with_zeroed(1))
            contributions["clinical_notes"] = abs(full_score - _score_with_zeroed(2))
            contributions["sdoh"] = abs(full_score - _score_with_zeroed(3))

            total = sum(contributions.values()) or 1.0
            contributions = {k: v / total for k, v in contributions.items()}

        except Exception as e:
            logger.debug(f"Could not compute modality contributions: {e}")
            contributions = {
                "ehr_structured": 0.50,
                "timeseries": 0.30,
                "clinical_notes": 0.10,
                "sdoh": 0.10,
            }

        return contributions

    @staticmethod
    def _categorize_risk(score: float) -> str:
        """Categorize risk score into clinical risk levels."""
        if score < 0.25:
            return "low"
        elif score < 0.50:
            return "moderate"
        elif score < 0.75:
            return "high"
        else:
            return "critical"

    def get_risk_explanation(self, patient_data: Dict[str, Any]) -> Dict:
        """
        Get full risk assessment with explanation for clinical decision support.
        """
        result = self.predict(patient_data, return_modality_contributions=True)

        ehr_features = self.extract_ehr_features(patient_data)
        top_risk_factors: List[Dict[str, str]] = []

        CHRONIC_NAMES = [
            "Type 2 Diabetes", "Hypertension", "Hyperlipidemia", "COPD",
            "Heart Failure", "CKD", "Depression", "Anxiety", "Obesity",
            "CAD", "Asthma", "Rheumatoid Arthritis", "GERD", "Sleep Apnea",
            "Hypothyroidism", "Back Pain", "Atrial Fibrillation", "UTI",
            "IBS", "Migraine",
        ]
        for i, name in enumerate(CHRONIC_NAMES):
            if ehr_features[34 + i] > 0:
                top_risk_factors.append({"factor": name, "type": "chronic_condition"})

        if ehr_features[55] > 0.2:
            top_risk_factors.append({"factor": "Recent ED visits", "type": "utilization"})
        if ehr_features[56] > 0.2:
            top_risk_factors.append({"factor": "Recent hospitalization", "type": "utilization"})

        result["top_risk_factors"] = top_risk_factors[:10]
        result["version"] = self.version

        return result
