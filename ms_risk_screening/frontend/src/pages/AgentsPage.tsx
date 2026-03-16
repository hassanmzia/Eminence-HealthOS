import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, CircularProgress,
  TextField, Button, Alert, Paper, Tabs, Tab,
} from '@mui/material';
import { SmartToy as AgentIcon, Hub as MCPIcon } from '@mui/icons-material';
import { getA2AAgents, getMCPTools, createMCPSession, invokeMCPTool } from '../services/api';
import type { A2AAgent, MCPTool } from '../types';

export default function AgentsPage() {
  const [agents, setAgents] = useState<A2AAgent[]>([]);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);
  const [selectedTool, setSelectedTool] = useState<string>('');
  const [toolArgs, setToolArgs] = useState('{}');
  const [toolResult, setToolResult] = useState<any>(null);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    Promise.all([
      getA2AAgents().then((r) => setAgents(r.data.agents || [])).catch(() => {}),
      getMCPTools().then((r) => setTools(r.data.tools || [])).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const handleInvoke = async () => {
    setExecuting(true);
    try {
      const session = await createMCPSession();
      const result = await invokeMCPTool(session.data.session_id, selectedTool, JSON.parse(toolArgs));
      setToolResult(result.data);
    } catch (e: any) {
      setToolResult({ error: e.message });
    }
    setExecuting(false);
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>AI Agent System</Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ display: { xs: 'none', sm: 'block' } }}>
        MCP (Model Context Protocol) tools and A2A (Agent-to-Agent) registry
      </Typography>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }} variant="scrollable" scrollButtons="auto" allowScrollButtonsMobile>
        <Tab icon={<AgentIcon />} label="A2A Agents" iconPosition="start" />
        <Tab icon={<MCPIcon />} label="MCP Tools" iconPosition="start" />
        <Tab label="Tool Playground" />
      </Tabs>

      {tab === 0 && (
        <Grid container spacing={3}>
          {agents.map((agent) => (
            <Grid item xs={12} md={6} lg={4} key={agent.agent_id}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <AgentIcon color="primary" />
                    <Typography variant="h6">{agent.name}</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{agent.description}</Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {agent.capabilities.map((cap) => (
                      <Chip key={cap} label={cap} size="small" variant="outlined" color="primary" />
                    ))}
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    v{agent.version} | ID: {agent.agent_id}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {tab === 1 && (
        <Grid container spacing={2}>
          {tools.map((tool) => (
            <Grid item xs={12} md={6} key={tool.name}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ fontFamily: 'monospace', fontSize: '1rem' }}>{tool.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{tool.description}</Typography>
                  <Paper variant="outlined" sx={{ p: 1, bgcolor: 'action.hover', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                    {JSON.stringify(tool.input_schema, null, 2)}
                  </Paper>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {tab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={5}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>MCP Tool Playground</Typography>
                <TextField select label="Select Tool" value={selectedTool} fullWidth size="small" sx={{ mb: 2 }}
                  onChange={(e) => setSelectedTool(e.target.value)}
                  SelectProps={{ native: true }}>
                  <option value="">-- Select a tool --</option>
                  {tools.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
                </TextField>
                <TextField label="Arguments (JSON)" value={toolArgs} onChange={(e) => setToolArgs(e.target.value)}
                  fullWidth multiline rows={6} size="small" sx={{ mb: 2, fontFamily: 'monospace' }} />
                <Button variant="contained" fullWidth onClick={handleInvoke}
                  disabled={!selectedTool || executing}
                  startIcon={executing ? <CircularProgress size={20} color="inherit" /> : <MCPIcon />}>
                  Invoke Tool
                </Button>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={7}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Result</Typography>
                {toolResult ? (
                  <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover', overflow: 'auto', maxHeight: 500 }}>
                    <pre style={{ margin: 0, fontSize: '0.8rem', fontFamily: 'monospace' }}>
                      {JSON.stringify(toolResult, null, 2)}
                    </pre>
                  </Paper>
                ) : (
                  <Typography color="text.secondary">Select a tool and invoke it to see results</Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
