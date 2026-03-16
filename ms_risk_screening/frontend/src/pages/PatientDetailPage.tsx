import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Grid, Typography, Card, CardContent, Chip, CircularProgress,
  Table, TableBody, TableCell, TableRow, Button, Divider, Alert, Paper,
} from '@mui/material';
import { ArrowBack as BackIcon, SmartToy as AgentIcon } from '@mui/icons-material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { getPatient, orchestrateScreening } from '../services/api';
import { RiskScoreBadge, ActionBadge, AutonomyBadge } from '../components/RiskBadge';
import { symptomLabels, getRiskColor } from '../utils/helpers';
import type { Patient, RiskAssessment } from '../types';

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<(Patient & { risk_assessments?: RiskAssessment[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [screeningLoading, setScreeningLoading] = useState(false);
  const [screeningResult, setScreeningResult] = useState<any>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getPatient(id)
      .then((r) => setPatient(r.data))
      .finally(() => setLoading(false));
  }, [id]);

  const handleA2AScreening = async () => {
    if (!patient) return;
    setScreeningLoading(true);
    try {
      const r = await orchestrateScreening(patient.patient_id);
      setScreeningResult(r.data);
    } catch (e) {
      setScreeningResult({ error: 'Screening failed' });
    }
    setScreeningLoading(false);
  };

  if (loading || !patient) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}><CircularProgress /></Box>;
  }

  const symptoms = [
    'optic_neuritis', 'paresthesia', 'weakness', 'gait_instability',
    'vertigo', 'fatigue', 'bladder_issues', 'cognitive_fog',
  ];
  const activeSymptoms = symptoms.filter((s) => (patient as any)[s]);
  const latestAssessment = patient.risk_assessments?.[0];

  const contribData = latestAssessment?.feature_contributions
    ? Object.entries(latestAssessment.feature_contributions)
        .filter(([_, v]) => v !== 0)
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        .slice(0, 10)
        .map(([k, v]) => ({ name: k.replace(/_/g, ' '), value: Number(v.toFixed(4)) }))
    : [];

  return (
    <Box>
      <Button startIcon={<BackIcon />} onClick={() => navigate('/patients')} sx={{ mb: 2 }}>
        Back to Patients
      </Button>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h4" sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>{patient.patient_id}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
            {patient.age}yo {patient.sex === 'F' ? 'Female' : 'Male'} | {patient.visits_last_year} visits/year | Dx: {patient.lookalike_dx}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={screeningLoading ? <CircularProgress size={20} color="inherit" /> : <AgentIcon />}
          onClick={handleA2AScreening}
          disabled={screeningLoading}
          sx={{ borderRadius: 3, flexShrink: 0, fontSize: { xs: '0.75rem', sm: '0.875rem' } }}
        >
          Run A2A Screening
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Demographics & Clinical Data</Typography>
              <Table size="small">
                <TableBody>
                  <TableRow><TableCell><strong>Age</strong></TableCell><TableCell>{patient.age}</TableCell></TableRow>
                  <TableRow><TableCell><strong>Sex</strong></TableCell><TableCell>{patient.sex}</TableCell></TableRow>
                  <TableRow><TableCell><strong>Visits/Year</strong></TableCell><TableCell>{patient.visits_last_year}</TableCell></TableRow>
                  <TableRow><TableCell><strong>Look-alike Dx</strong></TableCell><TableCell>{patient.lookalike_dx}</TableCell></TableRow>
                  <TableRow><TableCell><strong>Has MRI</strong></TableCell><TableCell>{patient.has_mri ? 'Yes' : 'No'}</TableCell></TableRow>
                  <TableRow><TableCell><strong>MRI Lesions</strong></TableCell><TableCell>{patient.mri_lesions ? 'Yes' : 'No'}</TableCell></TableRow>
                  <TableRow><TableCell><strong>Note MS Terms</strong></TableCell><TableCell>{patient.note_has_ms_terms ? 'Yes' : 'No'}</TableCell></TableRow>
                  <TableRow><TableCell><strong>Ground Truth</strong></TableCell><TableCell><Chip label={patient.true_at_risk ? 'At Risk' : 'Not At Risk'} size="small" color={patient.true_at_risk ? 'error' : 'success'} /></TableCell></TableRow>
                  {patient.vitamin_d_ngml != null && <TableRow><TableCell><strong>Vitamin D</strong></TableCell><TableCell>{patient.vitamin_d_ngml.toFixed(1)} ng/mL {patient.vitamin_d_deficient ? '(Deficient)' : ''}</TableCell></TableRow>}
                  {patient.infectious_mono_history != null && <TableRow><TableCell><strong>Mono History</strong></TableCell><TableCell>{patient.infectious_mono_history ? 'Yes' : 'No'}</TableCell></TableRow>}
                  {patient.smartform_neuro_symptom_score != null && <TableRow><TableCell><strong>Neuro Score</strong></TableCell><TableCell>{patient.smartform_neuro_symptom_score.toFixed(2)}</TableCell></TableRow>}
                  {patient.paths_like_function_score != null && <TableRow><TableCell><strong>Function Score</strong></TableCell><TableCell>{patient.paths_like_function_score.toFixed(1)}</TableCell></TableRow>}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Symptoms ({activeSymptoms.length}/8)</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {symptoms.map((s) => (
                  <Chip
                    key={s}
                    label={symptomLabels[s]}
                    color={(patient as any)[s] ? 'error' : 'default'}
                    variant={(patient as any)[s] ? 'filled' : 'outlined'}
                    size="small"
                  />
                ))}
              </Box>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Clinical Note</Typography>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover', fontFamily: 'monospace', fontSize: { xs: '0.75rem', sm: '0.85rem' }, wordBreak: 'break-word', overflowWrap: 'break-word' }}>
                {patient.note || 'No note available'}
              </Paper>
            </CardContent>
          </Card>
        </Grid>

        {latestAssessment && (
          <>
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>Latest Risk Assessment</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Risk Score</Typography>
                  <Box sx={{ textAlign: 'center', py: 2 }}>
                    <Typography variant="h2" sx={{ color: getRiskColor(latestAssessment.risk_score), fontWeight: 700 }}>
                      {latestAssessment.risk_score.toFixed(3)}
                    </Typography>
                    <Box sx={{ mt: 1 }}>
                      <ActionBadge action={latestAssessment.action} />
                      <Box sx={{ mt: 1 }}><AutonomyBadge level={latestAssessment.autonomy_level} /></Box>
                    </Box>
                  </Box>
                  {latestAssessment.flags && latestAssessment.flags.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>Safety Flags</Typography>
                      {latestAssessment.flags.map((f, i) => (
                        <Chip key={i} label={f} color="warning" size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                      ))}
                    </Box>
                  )}
                  {latestAssessment.rationale && latestAssessment.rationale.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>Decision Rationale</Typography>
                      {latestAssessment.rationale.map((r, i) => (
                        <Typography key={i} variant="body2" color="text.secondary">{'\u2022'} {r}</Typography>
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Feature Contributions</Typography>
                  {contribData.length > 0 ? (
                    <Box sx={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                    <ResponsiveContainer width="100%" height={350} minWidth={500}>
                      <BarChart data={contribData} layout="vertical" margin={{ left: 100 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
                        <RTooltip />
                        <Bar dataKey="value">
                          {contribData.map((entry, i) => (
                            <Cell key={i} fill={entry.value >= 0 ? '#1976d2' : '#d32f2f'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    </Box>
                  ) : (
                    <Typography color="text.secondary">No feature contribution data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {screeningResult && (
          <Grid item xs={12}>
            <Alert severity="info" sx={{ borderRadius: 2 }}>
              <Typography variant="subtitle2">A2A Screening Result</Typography>
              <pre style={{ fontSize: '0.8rem', overflow: 'auto', maxHeight: 300 }}>
                {JSON.stringify(screeningResult, null, 2)}
              </pre>
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
