import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Alert,
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Legend, RadarChart, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, Radar,
} from 'recharts';
import { getWorkflowRuns, getWorkflowFairness } from '../services/api';
import { formatPercent } from '../utils/helpers';
import type { SubgroupData } from '../types';

export default function FairnessPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [group, setGroup] = useState('sex');
  const [data, setData] = useState<SubgroupData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getWorkflowRuns().then((r) => {
      const completed = r.data.results.find((w: any) => w.status === 'COMPLETED');
      if (completed) setRunId(completed.id);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    getWorkflowFairness(runId, group).then((r) => setData(r.data)).finally(() => setLoading(false));
  }, [runId, group]);

  if (!runId && !loading) {
    return <Alert severity="info">No completed workflow runs. Run a screening workflow first.</Alert>;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.25rem', sm: '2.125rem' } }}>Fairness & Equity Dashboard</Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ display: { xs: 'none', sm: 'block' } }}>
        Responsible AI monitoring: stratified metrics by demographic and clinical groups
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
        {['sex', 'age_band', 'lookalike_dx'].map((g) => (
          <Chip key={g} label={g === 'sex' ? 'By Sex' : g === 'age_band' ? 'By Age Band' : 'By Diagnosis'} onClick={() => setGroup(g)} color={group === g ? 'primary' : 'default'} variant={group === g ? 'filled' : 'outlined'} sx={{ fontWeight: 600 }} />
        ))}
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
      ) : (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card><CardContent>
              <Typography variant="h6" gutterBottom>Flag Rate Comparison</Typography>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="group" />
                  <YAxis />
                  <RTooltip formatter={(v: number) => formatPercent(v)} />
                  <Legend />
                  <Bar dataKey="flagged_rate" fill="#1976d2" name="Flag Rate" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="true_at_risk_rate" fill="#4caf50" name="True At Risk" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="auto_or_draft_rate" fill="#f57c00" name="Auto/Draft Rate" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="safety_flag_rate" fill="#d32f2f" name="Safety Flag Rate" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent></Card>
          </Grid>

          <Grid item xs={12}>
            <Card><CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontSize: { xs: '1rem', sm: '1.25rem' } }}>Subgroup Metrics Table</Typography>
              <TableContainer sx={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Group</TableCell>
                    <TableCell align="right">N</TableCell>
                    <TableCell align="right">Flag Rate</TableCell>
                    <TableCell align="right">Avg Risk</TableCell>
                    <TableCell align="right">Auto/Draft Rate</TableCell>
                    <TableCell align="right">Auto Rate</TableCell>
                    <TableCell align="right">Safety Flag Rate</TableCell>
                    <TableCell align="right">True At Risk</TableCell>
                    <TableCell align="right">MRI Rate</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.map((row) => (
                    <TableRow key={row.group}>
                      <TableCell sx={{ fontWeight: 600 }}>{row.group}</TableCell>
                      <TableCell align="right">{row.n}</TableCell>
                      <TableCell align="right">{formatPercent(row.flagged_rate)}</TableCell>
                      <TableCell align="right">{row.avg_risk.toFixed(4)}</TableCell>
                      <TableCell align="right">{formatPercent(row.auto_or_draft_rate)}</TableCell>
                      <TableCell align="right">{formatPercent(row.auto_rate)}</TableCell>
                      <TableCell align="right">{formatPercent(row.safety_flag_rate)}</TableCell>
                      <TableCell align="right">{formatPercent(row.true_at_risk_rate)}</TableCell>
                      <TableCell align="right">{formatPercent(row.mri_rate)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </TableContainer>
            </CardContent></Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
