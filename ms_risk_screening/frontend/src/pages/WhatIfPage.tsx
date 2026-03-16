import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Slider, Button,
  CircularProgress, Alert, Divider,
} from '@mui/material';
import { Science as ScienceIcon } from '@mui/icons-material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Legend, Cell,
} from 'recharts';
import StatCard from '../components/StatCard';
import { getWorkflowRuns, runWhatIf } from '../services/api';
import { formatPercent } from '../utils/helpers';
import type { WhatIfResult } from '../types';

export default function WhatIfPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<WhatIfResult[]>([]);
  const [thresholds, setThresholds] = useState({
    risk_review_threshold: 0.65,
    draft_order_threshold: 0.80,
    auto_order_threshold: 0.90,
    max_auto_actions_per_day: 20,
  });

  useEffect(() => {
    getWorkflowRuns().then((r) => {
      const completed = r.data.results.find((w: any) => w.status === 'COMPLETED');
      if (completed) setRunId(completed.id);
    });
  }, []);

  const handleAnalyze = async () => {
    if (!runId) return;
    setLoading(true);
    try {
      const r = await runWhatIf({ run_id: runId, ...thresholds });
      setResults((prev) => [...prev, r.data]);
    } finally {
      setLoading(false);
    }
  };

  const presets = [
    { name: 'Conservative', values: { risk_review_threshold: 0.75, draft_order_threshold: 0.88, auto_order_threshold: 0.95, max_auto_actions_per_day: 10 } },
    { name: 'Balanced (Default)', values: { risk_review_threshold: 0.65, draft_order_threshold: 0.80, auto_order_threshold: 0.90, max_auto_actions_per_day: 20 } },
    { name: 'Aggressive', values: { risk_review_threshold: 0.50, draft_order_threshold: 0.70, auto_order_threshold: 0.85, max_auto_actions_per_day: 40 } },
    { name: 'No Auto', values: { risk_review_threshold: 0.65, draft_order_threshold: 0.80, auto_order_threshold: 1.01, max_auto_actions_per_day: 0 } },
  ];

  if (!runId) {
    return <Alert severity="info">No completed workflow runs. Run a screening workflow first.</Alert>;
  }

  const comparisonData = results.map((r, i) => ({
    name: `Scenario ${i + 1}`,
    flagged: r.results.flagged,
    precision: r.precision,
    recall: r.recall,
    auto: r.results.auto,
    draft: r.results.draft,
  }));

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.25rem', sm: '2.125rem' } }}>Policy What-If Analysis</Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ display: { xs: 'none', sm: 'block' } }}>
        Explore how policy threshold changes impact screening outcomes
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Threshold Configuration</Typography>

              <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap' }}>
                {presets.map((p) => (
                  <Button key={p.name} size="small" variant="outlined" onClick={() => setThresholds(p.values)}>
                    {p.name}
                  </Button>
                ))}
              </Box>

              <Typography gutterBottom>Review Threshold: {thresholds.risk_review_threshold.toFixed(2)}</Typography>
              <Slider value={thresholds.risk_review_threshold} min={0.3} max={1} step={0.01}
                onChange={(_, v) => setThresholds({ ...thresholds, risk_review_threshold: v as number })} />

              <Typography gutterBottom>Draft Order Threshold: {thresholds.draft_order_threshold.toFixed(2)}</Typography>
              <Slider value={thresholds.draft_order_threshold} min={0.3} max={1} step={0.01}
                onChange={(_, v) => setThresholds({ ...thresholds, draft_order_threshold: v as number })} />

              <Typography gutterBottom>Auto Order Threshold: {thresholds.auto_order_threshold.toFixed(2)}</Typography>
              <Slider value={thresholds.auto_order_threshold} min={0.3} max={1.01} step={0.01}
                onChange={(_, v) => setThresholds({ ...thresholds, auto_order_threshold: v as number })} />

              <Typography gutterBottom>Max Auto Actions/Day: {thresholds.max_auto_actions_per_day}</Typography>
              <Slider value={thresholds.max_auto_actions_per_day} min={0} max={100} step={1}
                onChange={(_, v) => setThresholds({ ...thresholds, max_auto_actions_per_day: v as number })} />

              <Button variant="contained" fullWidth startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <ScienceIcon />}
                onClick={handleAnalyze} disabled={loading} sx={{ mt: 2, borderRadius: 2 }}>
                Analyze Scenario
              </Button>
              {results.length > 0 && (
                <Button variant="text" fullWidth onClick={() => setResults([])} sx={{ mt: 1 }}>
                  Clear Results
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          {results.length > 0 ? (
            <>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                {results.map((r, i) => (
                  <React.Fragment key={i}>
                    <Grid item xs={4}><StatCard title={`S${i + 1} Flagged`} value={r.results.flagged} /></Grid>
                    <Grid item xs={4}><StatCard title={`S${i + 1} Precision`} value={formatPercent(r.precision)} color="#2e7d32" /></Grid>
                    <Grid item xs={4}><StatCard title={`S${i + 1} Recall`} value={formatPercent(r.recall)} color="#1565c0" /></Grid>
                  </React.Fragment>
                ))}
              </Grid>

              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Scenario Comparison</Typography>
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={comparisonData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RTooltip />
                      <Legend />
                      <Bar dataKey="flagged" fill="#1976d2" name="Flagged" />
                      <Bar dataKey="auto" fill="#d32f2f" name="Auto Orders" />
                      <Bar dataKey="draft" fill="#f57c00" name="Draft Orders" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <ScienceIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 2 }} />
                <Typography variant="h6" color="text.secondary">Configure thresholds and click Analyze</Typography>
                <Typography variant="body2" color="text.secondary">Compare multiple policy scenarios side-by-side</Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
