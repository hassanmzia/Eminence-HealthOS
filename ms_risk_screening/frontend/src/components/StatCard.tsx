import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  color?: string;
  trend?: { value: number; label: string };
}

export default function StatCard({ title, value, subtitle, icon, color = '#1976d2', trend }: StatCardProps) {
  return (
    <Card sx={{ height: '100%', position: 'relative', overflow: 'visible' }}>
      <CardContent sx={{ pb: '16px !important', px: { xs: 1.5, sm: 2 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom sx={{ fontSize: { xs: '0.7rem', sm: '0.875rem' } }}>
              {title}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, color, fontSize: { xs: '1.25rem', sm: '2.125rem' } }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
            {trend && (
              <Typography
                variant="caption"
                sx={{ color: trend.value >= 0 ? 'success.main' : 'error.main', fontWeight: 600 }}
              >
                {trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}
              </Typography>
            )}
          </Box>
          {icon && (
            <Box
              sx={{
                p: { xs: 1, sm: 1.5 },
                borderRadius: 2,
                bgcolor: `${color}15`,
                color,
                display: { xs: 'none', sm: 'flex' },
                alignItems: 'center',
                flexShrink: 0,
              }}
            >
              {icon}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
