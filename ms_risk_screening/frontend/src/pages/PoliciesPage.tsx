import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Button, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip,
  Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress,
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { getPolicies, createPolicy, activatePolicy } from '../services/api';
import { formatDate } from '../utils/helpers';
import type { PolicyConfiguration } from '../types';

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<PolicyConfiguration[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    name: '', risk_review_threshold: 0.65, draft_order_threshold: 0.80,
    auto_order_threshold: 0.90, max_auto_actions_per_day: 20, created_by: 'Admin',
  });

  const load = () => {
    setLoading(true);
    getPolicies().then((r) => setPolicies(r.data.results)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    await createPolicy(form);
    setDialogOpen(false);
    setForm({ name: '', risk_review_threshold: 0.65, draft_order_threshold: 0.80, auto_order_threshold: 0.90, max_auto_actions_per_day: 20, created_by: 'Admin' });
    load();
  };

  const handleActivate = async (id: string) => {
    await activatePolicy(id);
    load();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h4" sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>Policy Configurations</Typography>
          <Typography variant="body2" color="text.secondary">Manage screening threshold policies</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)} sx={{ flexShrink: 0 }}>New Policy</Button>
      </Box>

      <Card sx={{ overflow: 'hidden' }}>
        {loading ? <Box sx={{ p: 4, textAlign: 'center' }}><CircularProgress /></Box> : (
          <TableContainer sx={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell align="right">Review</TableCell>
                <TableCell align="right">Draft</TableCell>
                <TableCell align="right">Auto</TableCell>
                <TableCell align="right">Max Auto/Day</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created By</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {policies.map((p) => (
                <TableRow key={p.id}>
                  <TableCell sx={{ fontWeight: 600 }}>{p.name}</TableCell>
                  <TableCell align="right">{p.risk_review_threshold}</TableCell>
                  <TableCell align="right">{p.draft_order_threshold}</TableCell>
                  <TableCell align="right">{p.auto_order_threshold}</TableCell>
                  <TableCell align="right">{p.max_auto_actions_per_day}</TableCell>
                  <TableCell><Chip label={p.is_active ? 'Active' : 'Inactive'} size="small" color={p.is_active ? 'success' : 'default'} /></TableCell>
                  <TableCell>{p.created_by}</TableCell>
                  <TableCell sx={{ fontSize: '0.8rem' }}>{formatDate(p.created_at)}</TableCell>
                  <TableCell>
                    {!p.is_active && <Button size="small" onClick={() => handleActivate(p.id)}>Activate</Button>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </TableContainer>
        )}
      </Card>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Policy</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField label="Policy Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} fullWidth size="small" />
            <TextField label="Review Threshold" type="number" value={form.risk_review_threshold} onChange={(e) => setForm({ ...form, risk_review_threshold: parseFloat(e.target.value) })} fullWidth size="small" inputProps={{ step: 0.01, min: 0, max: 1 }} />
            <TextField label="Draft Order Threshold" type="number" value={form.draft_order_threshold} onChange={(e) => setForm({ ...form, draft_order_threshold: parseFloat(e.target.value) })} fullWidth size="small" inputProps={{ step: 0.01, min: 0, max: 1 }} />
            <TextField label="Auto Order Threshold" type="number" value={form.auto_order_threshold} onChange={(e) => setForm({ ...form, auto_order_threshold: parseFloat(e.target.value) })} fullWidth size="small" inputProps={{ step: 0.01, min: 0, max: 1 }} />
            <TextField label="Max Auto Actions/Day" type="number" value={form.max_auto_actions_per_day} onChange={(e) => setForm({ ...form, max_auto_actions_per_day: parseInt(e.target.value) })} fullWidth size="small" />
            <TextField label="Created By" value={form.created_by} onChange={(e) => setForm({ ...form, created_by: e.target.value })} fullWidth size="small" />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={!form.name}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
