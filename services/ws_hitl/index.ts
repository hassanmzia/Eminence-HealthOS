/**
 * HealthOS WebSocket HITL Server
 * Real-time communication for HITL approvals and agent updates.
 * Adapted from Health_Assistant ws-server for HealthOS multi-agent platform.
 *
 * Uses Socket.IO + Redis pub/sub for real-time HITL approval workflows,
 * query result streaming, and A2A broadcast relay.
 */

import express from 'express';
import { createServer } from 'http';
import { Server, Socket } from 'socket.io';
import { createClient } from 'redis';
import cors from 'cors';

interface QueryResult {
  session_id: string;
  status: string;
  query_type?: string;
  result?: string;
  requires_approval?: boolean;
  approval_details?: {
    generated_sql?: string;
    risk_assessment?: string;
    risk_score?: number;
  };
}

const app = express();
app.use(cors());
app.use(express.json());

const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Redis clients for pub/sub
const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379/3';
const redisSub = createClient({ url: redisUrl });
const redisPub = createClient({ url: redisUrl });

// Connected clients by session
const sessions: Map<string, Set<string>> = new Map();
const socketToSession: Map<string, string> = new Map();

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'healthos-ws-hitl' });
});

// Notify endpoint for backend services
app.post('/notify', (req, res) => {
  const { type, data } = req.body;

  switch (type) {
    case 'approval_required':
      notifyApprovalRequired(data);
      break;
    case 'query_result':
      notifyQueryResult(data);
      break;
    case 'agent_update':
      notifyAgentUpdate(data);
      break;
    default:
      console.log('Unknown notification type:', type);
  }

  res.json({ success: true });
});

// WebSocket connection handler
io.on('connection', (socket: Socket) => {
  console.log('Client connected:', socket.id);

  // Join a session
  socket.on('join_session', (sessionId: string) => {
    if (!sessions.has(sessionId)) {
      sessions.set(sessionId, new Set());
    }
    sessions.get(sessionId)!.add(socket.id);
    socketToSession.set(socket.id, sessionId);
    socket.join(sessionId);

    console.log(`Socket ${socket.id} joined session ${sessionId}`);
    socket.emit('session_joined', { sessionId });
  });

  // Leave session
  socket.on('leave_session', (sessionId: string) => {
    leaveSession(socket.id, sessionId);
  });

  // Submit query — forwards to HealthOS agent service
  socket.on('submit_query', async (data: { sessionId: string; query: string; userId?: string }) => {
    const { sessionId, query, userId = 'anonymous' } = data;

    try {
      const response = await fetch(
        `${process.env.AGENT_URL || 'http://localhost:4090'}/api/v1/agents/process`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, session_id: sessionId, user_id: userId })
        }
      );

      const result = await response.json() as QueryResult;

      if (result.requires_approval) {
        io.to(sessionId).emit('approval_required', {
          sessionId: result.session_id,
          generatedSql: result.approval_details?.generated_sql,
          queryType: result.query_type,
          riskAssessment: result.approval_details?.risk_assessment,
          riskScore: result.approval_details?.risk_score
        });
      } else {
        io.to(sessionId).emit('query_result', {
          sessionId: result.session_id,
          status: result.status,
          queryType: result.query_type,
          result: result.result
        });
      }
    } catch (error: any) {
      socket.emit('error', { message: error.message });
    }
  });

  // Submit HITL decision
  socket.on('submit_decision', async (data: {
    sessionId: string;
    decision: string;
    reviewerId: string;
    notes?: string;
  }) => {
    const { sessionId, decision, reviewerId, notes = '' } = data;

    try {
      const response = await fetch(
        `${process.env.AGENT_URL || 'http://localhost:4090'}/api/v1/agents/resume`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            decision,
            reviewer_id: reviewerId,
            notes
          })
        }
      );

      const result = await response.json() as QueryResult;

      io.to(sessionId).emit('decision_processed', {
        sessionId,
        status: result.status,
        result: result.result,
        decision,
        reviewerId
      });

    } catch (error: any) {
      socket.emit('error', { message: error.message });
    }
  });

  // Disconnect handler
  socket.on('disconnect', () => {
    const sessionId = socketToSession.get(socket.id);
    if (sessionId) {
      leaveSession(socket.id, sessionId);
    }
    console.log('Client disconnected:', socket.id);
  });
});

function leaveSession(socketId: string, sessionId: string) {
  const sockets = sessions.get(sessionId);
  if (sockets) {
    sockets.delete(socketId);
    if (sockets.size === 0) {
      sessions.delete(sessionId);
    }
  }
  socketToSession.delete(socketId);
}

function notifyApprovalRequired(data: any) {
  const { session_id, ...rest } = data;
  io.to(session_id).emit('approval_required', {
    sessionId: session_id,
    ...rest
  });
}

function notifyQueryResult(data: any) {
  const { session_id, ...rest } = data;
  io.to(session_id).emit('query_result', {
    sessionId: session_id,
    ...rest
  });
}

function notifyAgentUpdate(data: any) {
  io.emit('agent_update', data);
}

// Subscribe to Redis channels for real-time relay
async function setupRedisSubscriptions() {
  await redisSub.connect();
  await redisPub.connect();

  // HITL task notifications
  await redisSub.subscribe('hitl:new_task', (message) => {
    const data = JSON.parse(message);
    notifyApprovalRequired(data);
  });

  // HITL decision notifications
  await redisSub.subscribe('hitl:decision', (message) => {
    const data = JSON.parse(message);
    io.to(data.session_id).emit('decision_made', data);
  });

  // A2A broadcast relay
  await redisSub.subscribe('a2a:broadcast', (message) => {
    const data = JSON.parse(message);
    io.emit('agent_broadcast', data);
  });

  console.log('Redis subscriptions set up');
}

const PORT = process.env.WS_HITL_PORT || 3002;

async function start() {
  try {
    await setupRedisSubscriptions();

    httpServer.listen(PORT, () => {
      console.log(`HealthOS WebSocket HITL server running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start WebSocket HITL server:', error);
    process.exit(1);
  }
}

start();
