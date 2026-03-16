import React from 'react';
import { Chip } from '@mui/material';
import { getRiskColor, getActionColor, getActionLabel, getAutonomyColor, getAutonomyLabel } from '../utils/helpers';

export function RiskScoreBadge({ score }: { score: number }) {
  return (
    <Chip
      label={score.toFixed(3)}
      size="small"
      sx={{
        bgcolor: getRiskColor(score),
        color: score >= 0.65 ? '#fff' : '#000',
        fontWeight: 600,
        fontFamily: 'monospace',
      }}
    />
  );
}

export function ActionBadge({ action }: { action: string }) {
  return (
    <Chip
      label={getActionLabel(action)}
      size="small"
      sx={{
        bgcolor: `${getActionColor(action)}20`,
        color: getActionColor(action),
        fontWeight: 600,
        border: `1px solid ${getActionColor(action)}40`,
      }}
    />
  );
}

export function AutonomyBadge({ level }: { level: string }) {
  return (
    <Chip
      label={getAutonomyLabel(level)}
      size="small"
      sx={{
        bgcolor: `${getAutonomyColor(level)}20`,
        color: getAutonomyColor(level),
        fontWeight: 600,
        border: `1px solid ${getAutonomyColor(level)}40`,
      }}
    />
  );
}
