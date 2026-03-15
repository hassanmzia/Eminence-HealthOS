/**
 * Eminence HealthOS — A2A Gateway Server
 * WebSocket + REST server for agent-to-agent communication.
 */

import { createServer, IncomingMessage, ServerResponse } from "http";
import { WebSocketServer, WebSocket } from "ws";
import * as jwt from "jsonwebtoken";
import { A2AGateway } from "./a2a/gateway";

// ── Configuration ───────────────────────────────────────────────────────────

const PORT = parseInt(process.env.A2A_PORT || "3200", 10);
const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379";
const JWT_SECRET = process.env.JWT_SECRET || "healthos-dev-secret";

const gateway = new A2AGateway();

// ── Auth ────────────────────────────────────────────────────────────────────

function verifyToken(token: string): Record<string, unknown> | null {
  try {
    return jwt.verify(token, JWT_SECRET) as Record<string, unknown>;
  } catch {
    return null;
  }
}

// ── HTTP Helpers ────────────────────────────────────────────────────────────

function parseBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => {
      try {
        const text = Buffer.concat(chunks).toString();
        resolve(text ? JSON.parse(text) : {});
      } catch {
        reject(new Error("Invalid JSON"));
      }
    });
    req.on("error", reject);
  });
}

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

// ── Route Handlers ──────────────────────────────────────────────────────────

async function handleRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = req.url || "/";
  const method = req.method || "GET";

  // Health check
  if (method === "GET" && url === "/health") {
    send(res, 200, {
      status: "ok",
      service: "a2a-gateway",
      agents: gateway.listAgents().length,
    });
    return;
  }

  // Discovery document
  if (method === "GET" && url === "/.well-known/agent.json") {
    send(res, 200, gateway.getDiscoveryDocument());
    return;
  }

  // List agents
  if (method === "GET" && url === "/a2a/agents") {
    send(res, 200, { agents: gateway.listAgents() });
    return;
  }

  // Get agents by type
  if (method === "GET" && url.startsWith("/a2a/agents/type/")) {
    const type = url.split("/a2a/agents/type/")[1];
    send(res, 200, { agents: gateway.getAgentsByType(type) });
    return;
  }

  // Get agents by tier
  if (method === "GET" && url.startsWith("/a2a/agents/tier/")) {
    const tier = parseInt(url.split("/a2a/agents/tier/")[1], 10);
    send(res, 200, { agents: gateway.getAgentsByTier(tier) });
    return;
  }

  // Register agent
  if (method === "POST" && url === "/a2a/agents/register") {
    const body = await parseBody(req);
    gateway.registerAgent(body as any);
    send(res, 201, { status: "registered", agentId: body.id });
    return;
  }

  // Heartbeat
  if (method === "POST" && url.match(/^\/a2a\/agents\/[^/]+\/heartbeat$/)) {
    const agentId = url.split("/")[3];
    const ok = gateway.heartbeat(agentId);
    send(res, ok ? 200 : 404, { status: ok ? "ok" : "agent not found" });
    return;
  }

  // Submit task
  if (method === "POST" && url === "/a2a/tasks") {
    const body = await parseBody(req);
    const task = gateway.createTask(body as any);
    send(res, 201, { task });
    return;
  }

  // Get task status
  if (method === "GET" && url.startsWith("/a2a/tasks/")) {
    const taskId = url.split("/a2a/tasks/")[1];
    const task = gateway.getTask(taskId);
    if (task) {
      send(res, 200, { task });
    } else {
      send(res, 404, { error: "Task not found" });
    }
    return;
  }

  send(res, 404, { error: "Not found" });
}

// ── Server Start ────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  // Initialize Redis
  try {
    await gateway.initRedis(REDIS_URL);
  } catch (err) {
    console.warn("[A2A] Redis unavailable, running without pub/sub:", err);
  }

  // Create HTTP server
  const server = createServer(handleRequest);

  // Create WebSocket server
  const wss = new WebSocketServer({ server, path: "/ws" });

  wss.on("connection", (ws: WebSocket, req: IncomingMessage) => {
    // Extract JWT from query string
    const url = new URL(req.url || "/", `http://localhost:${PORT}`);
    const token = url.searchParams.get("token") || "";

    const decoded = verifyToken(token);
    if (!decoded) {
      ws.close(4001, "Unauthorized");
      return;
    }

    const agentId = decoded.agentId as string;
    if (!agentId) {
      ws.close(4002, "Missing agentId in token");
      return;
    }

    console.log(`[A2A] WebSocket connected: ${agentId}`);
    gateway.registerConnection(agentId, ws);

    ws.send(
      JSON.stringify({
        type: "RESPONSE",
        payload: { status: "connected", agentId },
      })
    );
  });

  server.listen(PORT, () => {
    console.log(`[A2A] HealthOS A2A Gateway listening on port ${PORT}`);
    console.log(`[A2A] WebSocket endpoint: ws://localhost:${PORT}/ws`);
    console.log(`[A2A] Discovery: http://localhost:${PORT}/.well-known/agent.json`);
  });
}

main().catch(console.error);
