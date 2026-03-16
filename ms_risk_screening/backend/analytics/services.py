"""Analytics services for fairness, metrics, and what-if analysis."""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from django.db.models import Avg
from patients.models import Patient, RiskAssessment, WorkflowRun, PolicyConfiguration


def confusion_counts(assessments_qs) -> Tuple[int, int, int, int]:
    """Compute TP, FP, TN, FN from assessments queryset."""
    tp = fp = tn = fn = 0
    for a in assessments_qs.select_related('patient'):
        predicted_positive = a.action != 'NO_ACTION'
        actual_positive = a.patient.true_at_risk
        if actual_positive and predicted_positive:
            tp += 1
        elif not actual_positive and predicted_positive:
            fp += 1
        elif not actual_positive and not predicted_positive:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def compute_workflow_metrics(run_id) -> Dict[str, Any]:
    """Compute comprehensive metrics for a workflow run."""
    run = WorkflowRun.objects.get(id=run_id)
    assessments = RiskAssessment.objects.filter(run_id=run_id)
    
    total = assessments.count()
    if total == 0:
        return {'error': 'No assessments found'}
    
    flagged = assessments.exclude(action='NO_ACTION')
    tp, fp, tn, fn = confusion_counts(assessments)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'run_id': str(run_id),
        'total_assessed': total,
        'flagged_count': flagged.count(),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1_score': round(f1, 4),
        'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'auto_actions': assessments.filter(action='AUTO_ORDER_MRI_AND_NOTIFY_NEURO').count(),
        'draft_actions': assessments.filter(action='DRAFT_MRI_ORDER').count(),
        'recommend_actions': assessments.filter(action='RECOMMEND_NEURO_REVIEW').count(),
        'no_actions': assessments.filter(action='NO_ACTION').count(),
        'safety_flag_rate': round(
            assessments.filter(flag_count__gt=0).count() / total, 4
        ) if total > 0 else 0.0,
        'avg_risk_score': round(
            assessments.aggregate(avg=Avg('risk_score'))['avg'] or 0, 4
        ),
    }


def subgroup_analysis(run_id, group_by: str) -> List[Dict[str, Any]]:
    """Compute fairness metrics stratified by a demographic/clinical group."""
    assessments = RiskAssessment.objects.filter(run_id=run_id).select_related('patient')
    
    if not assessments.exists():
        return []
    
    # Build dataframe from assessments
    rows = []
    for a in assessments:
        p = a.patient
        age_band = (
            '<30' if p.age < 30 else
            '30-39' if p.age < 40 else
            '40-49' if p.age < 50 else
            '50-59' if p.age < 60 else
            '60-69' if p.age < 70 else
            '70+'
        )
        rows.append({
            'sex': p.sex,
            'age_band': age_band,
            'lookalike_dx': p.lookalike_dx,
            'action': a.action,
            'risk_score': a.risk_score,
            'autonomy_level': a.autonomy_level,
            'flag_count': a.flag_count,
            'true_at_risk': int(p.true_at_risk),
            'has_mri': int(p.has_mri),
        })
    
    df = pd.DataFrame(rows)
    
    if group_by not in df.columns:
        return []
    
    results = []
    for group_val, gdf in df.groupby(group_by):
        n = len(gdf)
        flagged = (gdf['action'] != 'NO_ACTION').sum()
        auto_or_draft = gdf['autonomy_level'].isin(['DRAFT_ORDER', 'AUTO_ORDER_WITH_GUARDRAILS']).sum()
        auto_only = (gdf['autonomy_level'] == 'AUTO_ORDER_WITH_GUARDRAILS').sum()
        
        results.append({
            'group': str(group_val),
            'n': int(n),
            'flagged_rate': round(flagged / n, 4) if n > 0 else 0,
            'avg_risk': round(gdf['risk_score'].mean(), 4),
            'auto_or_draft_rate': round(auto_or_draft / n, 4) if n > 0 else 0,
            'auto_rate': round(auto_only / n, 4) if n > 0 else 0,
            'safety_flag_rate': round((gdf['flag_count'] > 0).sum() / n, 4) if n > 0 else 0,
            'true_at_risk_rate': round(gdf['true_at_risk'].mean(), 4),
            'mri_rate': round(gdf['has_mri'].mean(), 4),
        })
    
    return results


def risk_distribution(run_id) -> Dict[str, Any]:
    """Get risk score distribution data for visualization."""
    assessments = RiskAssessment.objects.filter(run_id=run_id)
    scores = list(assessments.values_list('risk_score', flat=True))
    
    if not scores:
        return {'bins': [], 'counts': [], 'stats': {}}
    
    scores_arr = np.array(scores)
    counts, bin_edges = np.histogram(scores_arr, bins=20, range=(0, 1))
    
    return {
        'bins': [round(b, 3) for b in bin_edges[:-1].tolist()],
        'counts': counts.tolist(),
        'stats': {
            'mean': round(float(scores_arr.mean()), 4),
            'median': round(float(np.median(scores_arr)), 4),
            'std': round(float(scores_arr.std()), 4),
            'min': round(float(scores_arr.min()), 4),
            'max': round(float(scores_arr.max()), 4),
            'q25': round(float(np.percentile(scores_arr, 25)), 4),
            'q75': round(float(np.percentile(scores_arr, 75)), 4),
        }
    }


def action_distribution(run_id) -> List[Dict[str, Any]]:
    """Get action type distribution."""
    assessments = RiskAssessment.objects.filter(run_id=run_id)
    action_counts = {}
    for a in assessments.values_list('action', flat=True):
        action_counts[a] = action_counts.get(a, 0) + 1
    return [{'action': k, 'count': v} for k, v in action_counts.items()]


def autonomy_distribution(run_id) -> List[Dict[str, Any]]:
    """Get autonomy level distribution."""
    assessments = RiskAssessment.objects.filter(run_id=run_id)
    level_counts = {}
    for a in assessments.values_list('autonomy_level', flat=True):
        level_counts[a] = level_counts.get(a, 0) + 1
    return [{'level': k, 'count': v} for k, v in level_counts.items()]


def calibration_data(run_id, n_bins=10) -> List[Dict[str, Any]]:
    """Compute calibration data (predicted risk vs actual at-risk rate)."""
    assessments = RiskAssessment.objects.filter(run_id=run_id).select_related('patient')
    
    pairs = [(a.risk_score, int(a.patient.true_at_risk)) for a in assessments]
    if not pairs:
        return []
    
    df = pd.DataFrame(pairs, columns=['predicted', 'actual'])
    df['bin'] = pd.cut(df['predicted'], bins=n_bins, labels=False)
    
    results = []
    for bin_idx, gdf in df.groupby('bin'):
        results.append({
            'bin': int(bin_idx),
            'mean_predicted': round(gdf['predicted'].mean(), 4),
            'mean_actual': round(gdf['actual'].mean(), 4),
            'count': len(gdf),
        })
    return results


def what_if_analysis(run_id, policy_overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Re-evaluate existing assessments with different policy thresholds."""
    assessments = RiskAssessment.objects.filter(run_id=run_id).select_related('patient')
    
    base_policy = {
        'risk_review_threshold': 0.65,
        'draft_order_threshold': 0.80,
        'auto_order_threshold': 0.90,
        'max_auto_actions_per_day': 20,
    }
    new_policy = {**base_policy, **policy_overrides}
    
    auto_count = 0
    results = {'flagged': 0, 'auto': 0, 'draft': 0, 'recommend': 0, 'no_action': 0}
    tp = fp = fn = tn = 0
    
    for a in assessments:
        risk = a.risk_score
        flags = a.flags or []
        true_positive = a.patient.true_at_risk
        
        action = 'NO_ACTION'
        if risk >= new_policy['risk_review_threshold']:
            action = 'RECOMMEND_NEURO_REVIEW'
        if risk >= new_policy['draft_order_threshold'] and len(flags) == 0:
            action = 'DRAFT_MRI_ORDER'
        if risk >= new_policy['auto_order_threshold'] and len(flags) == 0:
            if auto_count < new_policy['max_auto_actions_per_day']:
                action = 'AUTO_ORDER_MRI_AND_NOTIFY_NEURO'
                auto_count += 1
            else:
                action = 'DRAFT_MRI_ORDER'
        if len(flags) > 0 and action != 'NO_ACTION':
            action = 'RECOMMEND_NEURO_REVIEW'
        
        predicted_positive = action != 'NO_ACTION'
        if true_positive and predicted_positive:
            tp += 1
        elif not true_positive and predicted_positive:
            fp += 1
        elif not true_positive and not predicted_positive:
            tn += 1
        else:
            fn += 1
        
        if action == 'NO_ACTION':
            results['no_action'] += 1
        elif action == 'RECOMMEND_NEURO_REVIEW':
            results['recommend'] += 1
            results['flagged'] += 1
        elif action == 'DRAFT_MRI_ORDER':
            results['draft'] += 1
            results['flagged'] += 1
        elif action == 'AUTO_ORDER_MRI_AND_NOTIFY_NEURO':
            results['auto'] += 1
            results['flagged'] += 1
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    return {
        'policy': new_policy,
        'results': results,
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
    }
