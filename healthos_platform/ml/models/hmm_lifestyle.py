"""
Hidden Markov Model for lifestyle pattern detection.
Identifies patient behavioral states: active/sedentary, adherent/non-adherent, etc.

Adapted for HealthOS (FastAPI + SQLAlchemy). Django ORM references replaced
with plain-dict patient data interface.
"""

import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone as tz
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.hmm_lifestyle")

# HMM states representing lifestyle patterns
LIFESTYLE_STATES = {
    0: "active_adherent",
    1: "active_non_adherent",
    2: "sedentary_adherent",
    3: "sedentary_non_adherent",
}

N_STATES = len(LIFESTYLE_STATES)
N_OBSERVATIONS = 6  # [steps, glucose_variability, medication_taken, sleep_hours, calories, mood]


class HMMLifestyleModel:
    """
    Gaussian HMM for detecting patient lifestyle patterns from wearable and EHR data.

    States: active_adherent | active_non_adherent | sedentary_adherent | sedentary_non_adherent
    Observations: daily feature vector from device + EHR data
    """

    def __init__(self, model_path: str = None):
        self.model = None
        self.model_path = model_path
        self.version = "hmm_lifestyle_v1"
        self._is_loaded = False

        # Initial transition matrix (will be learned from data)
        self.transition_matrix = np.array([
            [0.7, 0.1, 0.1, 0.1],
            [0.2, 0.5, 0.1, 0.2],
            [0.2, 0.1, 0.5, 0.2],
            [0.1, 0.1, 0.2, 0.6],
        ])

        # Initial state probabilities
        self.initial_probs = np.array([0.4, 0.2, 0.2, 0.2])

    def build_model(self):
        """Build HMM using hmmlearn."""
        try:
            from hmmlearn.hmm import GaussianHMM

            model = GaussianHMM(
                n_components=N_STATES,
                covariance_type="diag",
                n_iter=100,
                random_state=42,
                verbose=False,
            )
            model.startprob_ = self.initial_probs
            model.transmat_ = self.transition_matrix
            return model
        except ImportError:
            logger.warning("hmmlearn not installed. Using manual HMM implementation.")
            return None

    def load(self):
        """Load or initialize the HMM model."""
        import pickle

        if self.model_path:
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info(f"HMM model loaded from {self.model_path}")
                self._is_loaded = True
                return
            except Exception as e:
                logger.warning(f"Could not load HMM model: {e}")

        self.model = self.build_model()
        self._is_loaded = True

    def extract_daily_features(
        self,
        patient_data: Dict,
        target_date: date,
    ) -> Optional[np.ndarray]:
        """
        Extract daily feature vector for a patient on a given date.

        Returns: [steps, glucose_variability, medication_taken, sleep_hours, calories, mood]

        ``patient_data`` should contain an ``observations`` list with dicts
        having at least ``code``, ``value``, ``effective_datetime`` keys.
        """
        day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=tz.utc)
        day_end = day_start + timedelta(days=1)

        observations = patient_data.get("observations", [])

        def _day_obs(code: str) -> List[Dict]:
            return [
                o for o in observations
                if o.get("code") == code
                and o.get("effective_datetime") is not None
                and day_start <= o["effective_datetime"] < day_end
            ]

        # Step count (LOINC 55423-8)
        steps_obs = _day_obs("55423-8")
        if steps_obs:
            steps_obs.sort(key=lambda o: o["effective_datetime"], reverse=True)
            steps = (float(steps_obs[0].get("value") or 0)) / 10000
        else:
            steps = 0.0

        # Glucose variability (CGM data)
        glucose_obs = _day_obs("2339-0")
        glucose_readings = [float(o["value"]) for o in glucose_obs if o.get("value") is not None]
        glucose_variability = float(np.std(glucose_readings)) / 50 if len(glucose_readings) >= 3 else 0.0

        # Medication adherence (binary)
        medication_taken = 1.0  # Default: assume adherent

        # Sleep hours (LOINC 93832-4)
        sleep_obs = _day_obs("93832-4")
        if sleep_obs:
            sleep_hours = (float(sleep_obs[0].get("value") or 7)) / 10
        else:
            sleep_hours = 0.7

        # Calories (LOINC 41981-2)
        calorie_obs = _day_obs("41981-2")
        if calorie_obs:
            calories = (float(calorie_obs[0].get("value") or 2000)) / 2500
        else:
            calories = 0.8

        # Mood/PHQ score (0-1 normalized)
        mood = 0.7

        return np.array([steps, glucose_variability, medication_taken, sleep_hours, calories, mood])

    def detect_state(self, observation_sequence: np.ndarray) -> Tuple[List[int], List[str]]:
        """
        Detect lifestyle states from an observation sequence.

        Args:
            observation_sequence: (T, N_OBSERVATIONS) array of daily features

        Returns:
            (state_sequence, state_labels)
        """
        if self.model is None:
            self.load()

        if len(observation_sequence) == 0:
            return [], []

        if self.model is not None:
            try:
                state_sequence = self.model.predict(observation_sequence)
                labels = [LIFESTYLE_STATES[s] for s in state_sequence]
                return state_sequence.tolist(), labels
            except Exception as e:
                logger.warning(f"HMM prediction failed: {e}")

        # Manual Viterbi fallback
        return self._viterbi_decode(observation_sequence)

    def _viterbi_decode(self, obs_seq: np.ndarray) -> Tuple[List[int], List[str]]:
        """Manual Viterbi decoding for HMM."""
        T = len(obs_seq)
        delta = np.zeros((T, N_STATES))
        psi = np.zeros((T, N_STATES), dtype=int)

        for s in range(N_STATES):
            delta[0, s] = self.initial_probs[s] * self._observation_prob(obs_seq[0], s)

        for t in range(1, T):
            for s in range(N_STATES):
                trans_probs = [delta[t-1, s_] * self.transition_matrix[s_, s] for s_ in range(N_STATES)]
                psi[t, s] = int(np.argmax(trans_probs))
                delta[t, s] = max(trans_probs) * self._observation_prob(obs_seq[t], s)

        state_seq = [int(np.argmax(delta[T-1]))]
        for t in range(T-1, 0, -1):
            state_seq.append(psi[t, state_seq[-1]])
        state_seq.reverse()

        labels = [LIFESTYLE_STATES[s] for s in state_seq]
        return state_seq, labels

    def _observation_prob(self, obs: np.ndarray, state: int) -> float:
        """Simple Gaussian emission probability."""
        means = {
            0: np.array([0.8, 0.2, 1.0, 0.8, 0.8, 0.8]),  # active_adherent
            1: np.array([0.8, 0.5, 0.3, 0.7, 0.7, 0.5]),  # active_non_adherent
            2: np.array([0.2, 0.3, 1.0, 0.8, 0.7, 0.7]),  # sedentary_adherent
            3: np.array([0.2, 0.6, 0.3, 0.5, 0.6, 0.4]),  # sedentary_non_adherent
        }
        std = 0.2
        diff = obs - means[state]
        return float(np.exp(-0.5 * np.dot(diff, diff) / (std ** 2)))

    def get_patient_lifestyle_summary(
        self,
        patient_data: Dict,
        days: int = 30,
    ) -> Dict:
        """Get lifestyle pattern summary for a patient over the past N days."""
        today = date.today()
        obs_sequence = []
        dates = []

        for i in range(days, 0, -1):
            d = today - timedelta(days=i)
            features = self.extract_daily_features(patient_data, d)
            if features is not None:
                obs_sequence.append(features)
                dates.append(d.isoformat())

        if not obs_sequence:
            return {"error": "No data available"}

        obs_array = np.array(obs_sequence)
        states, labels = self.detect_state(obs_array)

        state_counts = Counter(labels)
        dominant_state = state_counts.most_common(1)[0][0] if state_counts else "unknown"

        return {
            "dominant_state": dominant_state,
            "state_distribution": dict(state_counts),
            "days_analyzed": len(states),
            "state_sequence": list(zip(dates[-10:], labels[-10:])),
            "adherence_rate": sum(1 for s in labels if "adherent" in s and "non" not in s) / max(len(labels), 1),
            "activity_rate": sum(1 for s in labels if "active" in s) / max(len(labels), 1),
        }
