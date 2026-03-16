import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, TextField, MenuItem,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TablePagination, Chip, IconButton, Tooltip, CircularProgress,
} from '@mui/material';
import { Visibility as ViewIcon, Check as CheckIcon, Close as CloseIcon } from '@mui/icons-material';
import { getPatients } from '../services/api';
import type { Patient, PaginatedResponse } from '../types';

export default function PatientsPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ sex: '', lookalike_dx: '', true_at_risk: '' });

  useEffect(() => {
    setLoading(true);
    const params: Record<string, any> = {
      page: page + 1,
      page_size: rowsPerPage,
    };
    if (filters.sex) params.sex = filters.sex;
    if (filters.lookalike_dx) params.lookalike_dx = filters.lookalike_dx;
    if (filters.true_at_risk) params.true_at_risk = filters.true_at_risk;

    getPatients(params)
      .then((r) => {
        setPatients(r.data.results);
        setTotal(r.data.count);
      })
      .finally(() => setLoading(false));
  }, [page, rowsPerPage, filters]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>Patient Registry</Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ display: { xs: 'none', sm: 'block' } }}>
        Synthetic EHR patient population for MS risk screening
      </Typography>

      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', pb: '16px !important' }}>
          <TextField
            select label="Sex" value={filters.sex} size="small" sx={{ minWidth: 120 }}
            onChange={(e) => setFilters({ ...filters, sex: e.target.value })}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="F">Female</MenuItem>
            <MenuItem value="M">Male</MenuItem>
          </TextField>
          <TextField
            select label="Diagnosis" value={filters.lookalike_dx} size="small" sx={{ minWidth: 160 }}
            onChange={(e) => setFilters({ ...filters, lookalike_dx: e.target.value })}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="none">None</MenuItem>
            <MenuItem value="migraine">Migraine</MenuItem>
            <MenuItem value="b12_deficiency">B12 Deficiency</MenuItem>
            <MenuItem value="anxiety">Anxiety</MenuItem>
            <MenuItem value="fibromyalgia">Fibromyalgia</MenuItem>
            <MenuItem value="stroke_TIA">Stroke/TIA</MenuItem>
          </TextField>
          <TextField
            select label="At Risk" value={filters.true_at_risk} size="small" sx={{ minWidth: 120 }}
            onChange={(e) => setFilters({ ...filters, true_at_risk: e.target.value })}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="true">At Risk</MenuItem>
            <MenuItem value="false">Not At Risk</MenuItem>
          </TextField>
        </CardContent>
      </Card>

      <Card sx={{ overflow: 'hidden' }}>
        <TableContainer sx={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Patient ID</TableCell>
                  <TableCell>Age</TableCell>
                  <TableCell>Sex</TableCell>
                  <TableCell>Diagnosis</TableCell>
                  <TableCell align="center">Symptoms</TableCell>
                  <TableCell align="center">MRI</TableCell>
                  <TableCell align="center">Lesions</TableCell>
                  <TableCell align="center">MS Terms</TableCell>
                  <TableCell align="center">At Risk</TableCell>
                  <TableCell align="center">Visits/Yr</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {patients.map((p) => (
                  <TableRow key={p.id} hover>
                    <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>{p.patient_id}</TableCell>
                    <TableCell>{p.age}</TableCell>
                    <TableCell>{p.sex}</TableCell>
                    <TableCell>
                      <Chip label={p.lookalike_dx} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={p.symptom_count} size="small" color={p.symptom_count >= 2 ? 'warning' : 'default'} />
                    </TableCell>
                    <TableCell align="center">{p.has_mri ? <CheckIcon color="success" fontSize="small" /> : <CloseIcon color="disabled" fontSize="small" />}</TableCell>
                    <TableCell align="center">{p.mri_lesions ? <CheckIcon color="error" fontSize="small" /> : <CloseIcon color="disabled" fontSize="small" />}</TableCell>
                    <TableCell align="center">{p.note_has_ms_terms ? <CheckIcon color="warning" fontSize="small" /> : <CloseIcon color="disabled" fontSize="small" />}</TableCell>
                    <TableCell align="center">
                      <Chip label={p.true_at_risk ? 'Yes' : 'No'} size="small" color={p.true_at_risk ? 'error' : 'success'} />
                    </TableCell>
                    <TableCell align="center">{p.visits_last_year}</TableCell>
                    <TableCell align="center">
                      <Tooltip title="View Details">
                        <IconButton size="small" onClick={() => navigate(`/patients/${p.id}`)}>
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={total}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value)); setPage(0); }}
        />
      </Card>
    </Box>
  );
}
