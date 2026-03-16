import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Grid, Typography, Card, CardContent, Button, CircularProgress,
  Chip, Divider, Tab, Tabs,
} from '@mui/material';
import { ArrowBack as BackIcon } from '@mui/icons-material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, LineChart, Line, ScatterChart, Scatter, Cell,
  AreaChart, Area, Legend,
} from 'recharts';
import StatCard from '../components/StatCard';
import {
  getWorkflowRun, getWorkflowMetrics, getWorkflowRiskDistribution,
  getWorkflowFairness, getWorkflowCalibration,
} from '../services/api';
import { formatPercent } from '../utils/helpers';

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [riskDist, setRiskDist] = useState<any>(null);
  const [fairness, setFairness] = useState<any[]>([]);
  const [calibration, setCalibration] = useState<any[]>([]);
  const [tab, setTab] = useState(0);
  const [fairnessGroup, setFairnessGroup] = useState('sex');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      getWorkflowRun(id).then((r) => setRun(r.data)),
      getWorkflowMetrics(id).then((r) => setMetrics(r.data)),
      getWorkflowRiskDistribution(id).then((r) => setRiskDist(r.data)),
      getWorkflowCalibration(id).then((r) => setCalibration(r.data)),
      getWorkflowFairness(id, 'sex').then((r) => setFairness(r.data)),
    ]).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    getWorkflowFairness(id, fairnessGroup).then((r) => setFairness(r.data));
  }, [id, fairnessGroup]);

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}><CircularProgress /></Box>;
  }

  const distData = riskDist?.bins?.map((b: number, i: number) => ({
    bin: b.toFixed(2), count: riskDist.counts[i],
  })) || [];

  return (
    <Box>
      <Button startIcon={<BackIcon />} onClick={() => navigate('/workflows')} sx={{ mb: 2 }}>Back to Workflows</Button>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>Workflow Run Details</Typography>
      {run && <Chip label={run.status} color={run.status === 'COMPLETED' ? 'success' : 'error'} sx={{ mb: 2 }} />}

      {metrics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={6} md={2}><StatCard title="Assessed" value={metrics.total_assessed} /></Grid>
          <Grid item xs={6} md={2}><StatCard title="Flagged" value={metrics.flagged_count} color="#f57c00" /></Grid>
          <Grid item xs={6} md={2}><StatCard title="Precision" value={formatPercent(metrics.precision)} color="#2e7d32" /></Grid>
          <Grid item xs={6} md={2}><StatCard title="Recall" value={formatPercent(metrics.recall)} color="#1565c0" /></Grid>
          <Grid item xs={6} md={2}><StatCard title="F1 Score" value={formatPercent(metrics.f1_score)} color="#7b1fa2" /></Grid>
          <Grid item xs={6} md={2}><StatCard title="Safety Flags" value={formatPercent(metrics.safety_flag_rate)} color="#d32f2f" /></Grid>
        </Grid>
      )}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }} variant="scrollable" scrollButtons="auto" allowScrollButtonsMobile>
        <Tab label="Risk Distribution" />
        <Tab label="Calibration" />
        <Tab label="Fairness Analysis" />
        <Tab label="Confusion Matrix" />
      </Tabs>

      {tab === 0 && (
        <Card><CardContent>
          <Typography variant="h6" gutterBottom>Risk Score Distribution</Typography>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={distData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bin" />
              <YAxis />
              <RTooltip />
              <Bar dataKey="count" fill="#1976d2" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          {riskDist?.stats && (
            <Box sx={{ display: 'flex', gap: 3, mt: 2, flexWrap: 'wrap' }}>
              <Typography variant="body2">Mean: {riskDist.stats.mean.toFixed(4)}</Typography>
              <Typography variant="body2">Median: {riskDist.stats.median.toFixed(4)}</Typography>
              <Typography variant="body2">Std: {riskDist.stats.std.toFixed(4)}</Typography>
              <Typography variant="body2">Q25: {riskDist.stats.q25.toFixed(4)}</Typography>
              <Typography variant="body2">Q75: {riskDist.stats.q75.toFixed(4)}</Typography>
            </Box>
          )}
        </CardContent></Card>
      )}

      {tab === 1 && (
        <Card><CardContent>
          <Typography variant="h6" gutterBottom>Calibration Plot (Predicted vs Actual)</Typography>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={calibration}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="mean_predicted" label={{ value: 'Predicted Risk', position: 'bottom' }} />
              <YAxis label={{ value: 'Actual At-Risk Rate', angle: -90, position: 'insideLeft' }} />
              <RTooltip />
              <Legend />
              <Line type="monotone" dataKey="mean_actual" stroke="#1976d2" name="Actual" strokeWidth={2} dot={{ r: 5 }} />
              <Line type="monotone" dataKey="mean_predicted" stroke="#ccc" name="Perfect Calibration" strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent></Card>
      )}

      {tab === 2 && (
        <Card><CardContent>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            {['sex', 'age_band', 'lookalike_dx'].map((g) => (
              <Chip key={g} label={g.replace('_', ' ')} onClick={() => setFairnessGroup(g)} color={fairnessGroup === g ? 'primary' : 'default'} variant={fairnessGroup === g ? 'filled' : 'outlined'} />
            ))}
          </Box>
          <Typography variant="h6" gutterBottom>Fairness: Flag Rate by {fairnessGroup}</Typography>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={fairness}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="group" />
              <YAxis />
              <RTooltip />
              <Legend />
              <Bar dataKey="flagged_rate" fill="#1976d2" name="Flag Rate" radius={[4, 4, 0, 0]} />
              <Bar dataKey="true_at_risk_rate" fill="#4caf50" name="True At Risk Rate" radius={[4, 4, 0, 0]} />
              <Bar dataKey="auto_rate" fill="#d32f2f" name="Auto Rate" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent></Card>
      )}

      {tab === 3 && metrics && (
        <Card><CardContent>
          <Typography variant="h6" gutterBottom>Confusion Matrix</Typography>
          <Grid container spacing={2} sx={{ maxWidth: 400, mx: 'auto', mt: 2 }}>
            <Grid item xs={6}>
              <Card sx={{ bgcolor: '#e8f5e9', textAlign: 'center', p: 2 }}>
                <Typography variant="h4" color="success.main">{metrics.tp}</Typography>
                <Typography variant="body2">True Positive</Typography>
              </Card>
            </Grid>
            <Grid item xs={6}>
              <Card sx={{ bgcolor: '#ffebee', textAlign: 'center', p: 2 }}>
                <Typography variant="h4" color="error.main">{metrics.fp}</Typography>
                <Typography variant="body2">False Positive</Typography>
              </Card>
            </Grid>
            <Grid item xs={6}>
              <Card sx={{ bgcolor: '#fff3e0', textAlign: 'center', p: 2 }}>
                <Typography variant="h4" color="warning.main">{metrics.fn}</Typography>
                <Typography variant="body2">False Negative</Typography>
              </Card>
            </Grid>
            <Grid item xs={6}>
              <Card sx={{ bgcolor: '#e3f2fd', textAlign: 'center', p: 2 }}>
                <Typography variant="h4" color="info.main">{metrics.tn}</Typography>
                <Typography variant="body2">True Negative</Typography>
              </Card>
            </Grid>
          </Grid>
        </CardContent></Card>
      )}
    </Box>
  );
}
