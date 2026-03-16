import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, TextField, MenuItem,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TablePagination, CircularProgress, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, Chip,
} from '@mui/material';
import { RiskScoreBadge, ActionBadge, AutonomyBadge } from '../components/RiskBadge';
import { getAssessments, reviewAssessment } from '../services/api';
import { formatDate } from '../utils/helpers';
import type { RiskAssessment, PaginatedResponse } from '../types';

export default function AssessmentsPage() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<RiskAssessment[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [reviewDialog, setReviewDialog] = useState<RiskAssessment | null>(null);
  const [reviewBy, setReviewBy] = useState('Dr. Smith');
  const [reviewNotes, setReviewNotes] = useState('');

  const load = () => {
    setLoading(true);
    const params: Record<string, any> = { page: page + 1, page_size: rowsPerPage };
    if (actionFilter) params.action = actionFilter;
    getAssessments(params)
      .then((r) => { setAssessments(r.data.results); setTotal(r.data.count); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, rowsPerPage, actionFilter]);

  const handleReview = async () => {
    if (!reviewDialog) return;
    await reviewAssessment(reviewDialog.id, { reviewed_by: reviewBy, review_notes: reviewNotes });
    setReviewDialog(null);
    setReviewNotes('');
    load();
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>Risk Assessments</Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ display: { xs: 'none', sm: 'block' } }}>
        Patient risk assessments from multi-agent screening workflow
      </Typography>

      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ display: 'flex', gap: 2, pb: '16px !important' }}>
          <TextField
            select label="Action" value={actionFilter} size="small" sx={{ minWidth: 200 }}
            onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
          >
            <MenuItem value="">All Actions</MenuItem>
            <MenuItem value="NO_ACTION">No Action</MenuItem>
            <MenuItem value="RECOMMEND_NEURO_REVIEW">Recommend Review</MenuItem>
            <MenuItem value="DRAFT_MRI_ORDER">Draft MRI Order</MenuItem>
            <MenuItem value="AUTO_ORDER_MRI_AND_NOTIFY_NEURO">Auto Order MRI</MenuItem>
          </TextField>
        </CardContent>
      </Card>

      <Card sx={{ overflow: 'hidden' }}>
        <TableContainer sx={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Patient</TableCell>
                  <TableCell>Risk Score</TableCell>
                  <TableCell>Action</TableCell>
                  <TableCell>Autonomy</TableCell>
                  <TableCell align="center">Flags</TableCell>
                  <TableCell>Reviewed</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {assessments.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell
                      sx={{ fontFamily: 'monospace', fontWeight: 600, cursor: 'pointer', color: 'primary.main' }}
                      onClick={() => navigate(`/patients/${a.patient}`)}
                    >
                      {a.patient_display}
                    </TableCell>
                    <TableCell><RiskScoreBadge score={a.risk_score} /></TableCell>
                    <TableCell><ActionBadge action={a.action} /></TableCell>
                    <TableCell><AutonomyBadge level={a.autonomy_level} /></TableCell>
                    <TableCell align="center">
                      {a.flag_count > 0 ? (
                        <Chip label={a.flag_count} size="small" color="warning" />
                      ) : (
                        <Chip label="0" size="small" color="success" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>
                      {a.reviewed_at ? (
                        <Chip label={a.reviewed_by} size="small" color="success" variant="outlined" />
                      ) : (
                        <Chip label="Pending" size="small" color="warning" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8rem' }}>{formatDate(a.created_at)}</TableCell>
                    <TableCell>
                      {!a.reviewed_at && a.action !== 'NO_ACTION' && (
                        <Button size="small" variant="outlined" onClick={() => setReviewDialog(a)}>
                          Review
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div" count={total} rowsPerPage={rowsPerPage} page={page}
          onPageChange={(_, p) => setPage(p)}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value)); setPage(0); }}
        />
      </Card>

      <Dialog open={!!reviewDialog} onClose={() => setReviewDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Review Assessment - {reviewDialog?.patient_display}</DialogTitle>
        <DialogContent>
          {reviewDialog && (
            <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <RiskScoreBadge score={reviewDialog.risk_score} />
                <ActionBadge action={reviewDialog.action} />
              </Box>
              <TextField label="Reviewer" value={reviewBy} onChange={(e) => setReviewBy(e.target.value)} fullWidth size="small" />
              <TextField label="Review Notes" value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} fullWidth multiline rows={3} size="small" />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDialog(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleReview}>Submit Review</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
