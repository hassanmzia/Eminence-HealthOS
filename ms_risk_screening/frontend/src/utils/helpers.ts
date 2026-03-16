export const formatPercent = (value: number | null | undefined): string => {
  if (value == null) return 'N/A';
  return `${(value * 100).toFixed(1)}%`;
};

export const formatScore = (value: number | null | undefined): string => {
  if (value == null) return 'N/A';
  return value.toFixed(4);
};

export const getActionColor = (action: string): string => {
  switch (action) {
    case 'AUTO_ORDER_MRI_AND_NOTIFY_NEURO': return '#d32f2f';
    case 'DRAFT_MRI_ORDER': return '#f57c00';
    case 'RECOMMEND_NEURO_REVIEW': return '#1976d2';
    case 'NO_ACTION': return '#4caf50';
    default: return '#757575';
  }
};

export const getActionLabel = (action: string): string => {
  switch (action) {
    case 'AUTO_ORDER_MRI_AND_NOTIFY_NEURO': return 'Auto Order MRI';
    case 'DRAFT_MRI_ORDER': return 'Draft MRI Order';
    case 'RECOMMEND_NEURO_REVIEW': return 'Recommend Review';
    case 'NO_ACTION': return 'No Action';
    default: return action;
  }
};

export const getAutonomyColor = (level: string): string => {
  switch (level) {
    case 'AUTO_ORDER_WITH_GUARDRAILS': return '#d32f2f';
    case 'DRAFT_ORDER': return '#f57c00';
    case 'RECOMMEND_ONLY': return '#1976d2';
    default: return '#757575';
  }
};

export const getAutonomyLabel = (level: string): string => {
  switch (level) {
    case 'AUTO_ORDER_WITH_GUARDRAILS': return 'Auto with Guardrails';
    case 'DRAFT_ORDER': return 'Draft Order';
    case 'RECOMMEND_ONLY': return 'Recommend Only';
    default: return level;
  }
};

export const getRiskColor = (score: number): string => {
  if (score >= 0.9) return '#d32f2f';
  if (score >= 0.8) return '#f57c00';
  if (score >= 0.65) return '#ffa726';
  if (score >= 0.4) return '#ffee58';
  return '#4caf50';
};

export const getSeverityColor = (severity: string): 'error' | 'warning' | 'info' | 'success' => {
  switch (severity) {
    case 'critical': return 'error';
    case 'warning': return 'warning';
    case 'success': return 'success';
    default: return 'info';
  }
};

export const formatDate = (dateStr: string): string => {
  return new Date(dateStr).toLocaleString();
};

export const symptomLabels: Record<string, string> = {
  optic_neuritis: 'Optic Neuritis',
  paresthesia: 'Paresthesia',
  weakness: 'Weakness',
  gait_instability: 'Gait Instability',
  vertigo: 'Vertigo',
  fatigue: 'Fatigue',
  bladder_issues: 'Bladder Issues',
  cognitive_fog: 'Cognitive Fog',
};
