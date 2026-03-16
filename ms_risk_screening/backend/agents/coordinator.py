"""Coordinator agent -- makes the final disposition decision."""
import logging
from typing import Any, Dict, List, Optional

from .base import AgentOutput, BaseAgent, AgentRegistry

logger = logging.getLogger('agents')

# ---------------------------------------------------------------------------
# Default policy thresholds (can be overridden via PolicyConfig)
# ---------------------------------------------------------------------------
DEFAULT_POLICY: Dict[str, Any] = {
    'risk_review_threshold': 0.65,
    'draft_order_threshold': 0.80,
    'auto_order_threshold': 0.90,
    'max_auto_actions_per_day': 20,
}


class Coordinator(BaseAgent):
    """
    Takes a phenotyping risk score and safety payload and emits a
    final action recommendation at one of four autonomy levels:

        NO_ACTION
            Risk below review threshold -- no further action.
        RECOMMEND_NEURO_REVIEW
            Risk warrants human review but not an automated order.
        DRAFT_MRI_ORDER
            System drafts an MRI order for clinician sign-off.
        AUTO_ORDER_MRI_AND_NOTIFY_NEURO
            System places the order automatically and notifies
            the neurologist (subject to rate limit).

    Safety override
    ---------------
    If the safety payload contains any flags, the coordinator
    downgrades any automated action to ``RECOMMEND_NEURO_REVIEW``
    (i.e. RECOMMEND_ONLY mode).
    """

    name = "coordinator"

    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        self.policy = {**DEFAULT_POLICY, **(policy or {})}
        self.auto_actions_used: int = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_rate_limit(self):
        """Call at the start of each daily run / workflow to reset the counter."""
        self.auto_actions_used = 0

    def _can_auto_act(self) -> bool:
        return self.auto_actions_used < self.policy['max_auto_actions_per_day']

    # ------------------------------------------------------------------
    # Core decision logic
    # ------------------------------------------------------------------

    def execute(
        self,
        risk: float,
        safety_payload: Dict[str, Any],
    ) -> AgentOutput:
        """
        Parameters
        ----------
        risk : float
            The phenotyping risk score (0-1).
        safety_payload : dict
            Output payload from the SafetyGovernanceAgent (must contain
            ``flags`` list and ``flag_count``).

        Returns
        -------
        AgentOutput with payload keys:
            action          -- str  final action code
            autonomy_level  -- int  (0-3)
            rationale       -- list[str]
        """
        flags: List[str] = safety_payload.get('flags', [])
        flag_count: int = safety_payload.get('flag_count', 0)
        rationale: List[str] = []

        review_thresh = self.policy['risk_review_threshold']
        draft_thresh = self.policy['draft_order_threshold']
        auto_thresh = self.policy['auto_order_threshold']

        # --- Determine raw action from risk score ---
        if risk < review_thresh:
            action = 'NO_ACTION'
            autonomy_level = 0
            rationale.append(
                f"Risk score {risk:.3f} is below the review threshold "
                f"({review_thresh})."
            )

        elif risk < draft_thresh:
            action = 'RECOMMEND_NEURO_REVIEW'
            autonomy_level = 1
            rationale.append(
                f"Risk score {risk:.3f} is between the review threshold "
                f"({review_thresh}) and the draft-order threshold "
                f"({draft_thresh})."
            )

        elif risk < auto_thresh:
            action = 'DRAFT_MRI_ORDER'
            autonomy_level = 2
            rationale.append(
                f"Risk score {risk:.3f} is between the draft-order threshold "
                f"({draft_thresh}) and the auto-order threshold "
                f"({auto_thresh})."
            )

        else:
            # Auto-order path, but subject to rate limiting
            if self._can_auto_act():
                action = 'AUTO_ORDER_MRI_AND_NOTIFY_NEURO'
                autonomy_level = 3
                self.auto_actions_used += 1
                rationale.append(
                    f"Risk score {risk:.3f} exceeds auto-order threshold "
                    f"({auto_thresh}). Auto-action count: "
                    f"{self.auto_actions_used}/"
                    f"{self.policy['max_auto_actions_per_day']}."
                )
            else:
                action = 'DRAFT_MRI_ORDER'
                autonomy_level = 2
                rationale.append(
                    f"Risk score {risk:.3f} exceeds auto-order threshold "
                    f"({auto_thresh}) but daily auto-action cap "
                    f"({self.policy['max_auto_actions_per_day']}) reached. "
                    f"Downgrading to DRAFT_MRI_ORDER."
                )

        # --- Safety flag override ---
        if flag_count > 0 and autonomy_level >= 2:
            original_action = action
            action = 'RECOMMEND_NEURO_REVIEW'
            autonomy_level = 1
            rationale.append(
                f"Safety override: {flag_count} flag(s) detected {flags}. "
                f"Downgrading from {original_action} to RECOMMEND_ONLY."
            )

        logger.info(
            f"Coordinator: action={action} autonomy={autonomy_level} "
            f"risk={risk:.3f} flags={flags}"
        )

        payload = {
            'action': action,
            'autonomy_level': autonomy_level,
            'rationale': rationale,
        }

        return AgentOutput(
            agent=self.name,
            patient_id='POLICY',
            payload=payload,
        )


# Register with default policy
coordinator_agent = Coordinator()
AgentRegistry.register(coordinator_agent)
