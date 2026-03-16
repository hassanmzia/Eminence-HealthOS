import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Button, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip,
} from '@mui/material';
import { PlayArrow as PlayIcon } from '@mui/icons-material';
import { getWorkflowRuns, triggerWorkflow } from '../services/api';
import { formatPercent, formatDate } from '../utils/helpers';
import type { WorkflowRun } from '../types';

export default function WorkflowsPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggerLoading, setTriggerLoading] = useState(false);

  const load = () => {
    setLoading(true);
    getWorkflowRuns().then((r) => setRuns(r.data.results)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleTrigger = async () => {
    setTriggerLoading(true);
    try {
      await triggerWorkflow();
      setTimeout(load, 3000);
    } finally {
      setTriggerLoading(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h4" sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>Workflow Runs</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>Multi-agent screening workflow execution history</Typography>
        </Box>
        <Button variant="contained" startIcon={triggerLoading ? <CircularProgress size={20} color="inherit" /> : <PlayIcon />} onClick={handleTrigger} disabled={triggerLoading} sx={{ flexShrink: 0 }}>
          New Workflow Run
        </Button>
      </Box>

      <Card sx={{ overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <TableContainer sx={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Run ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Policy</TableCell>
                  <TableCell align="right">Total</TableCell>
                  <TableCell align="right">Candidates</TableCell>
                  <TableCell align="right">Flagged</TableCell>
                  <TableCell align="right">Precision</TableCell>
                  <TableCell align="right">Recall</TableCell>
                  <TableCell align="right">Auto</TableCell>
                  <TableCell align="right">Draft</TableCell>
                  <TableCell align="right">Duration</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id} hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/workflows/${run.id}`)}>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{run.id.slice(0, 8)}...</TableCell>
                    <TableCell>
                      <Chip label={run.status} size="small" color={run.status === 'COMPLETED' ? 'success' : run.status === 'FAILED' ? 'error' : run.status === 'RUNNING' ? 'warning' : 'default'} />
                    </TableCell>
                    <TableCell>{run.policy_name || 'Default'}</TableCell>
                    <TableCell align="right">{run.total_patients}</TableCell>
                    <TableCell align="right">{run.candidates_found}</TableCell>
                    <TableCell align="right">{run.flagged_count}</TableCell>
                    <TableCell align="right">{formatPercent(run.precision)}</TableCell>
                    <TableCell align="right">{formatPercent(run.recall)}</TableCell>
                    <TableCell align="right">{run.auto_actions}</TableCell>
                    <TableCell align="right">{run.draft_actions}</TableCell>
                    <TableCell align="right">{run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : '-'}</TableCell>
                    <TableCell sx={{ fontSize: '0.8rem' }}>{formatDate(run.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
    </Box>
  );
}
