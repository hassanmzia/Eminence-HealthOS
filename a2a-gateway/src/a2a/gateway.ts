/**
 * Eminence HealthOS — A2A Gateway
 * Agent-to-Agent protocol gateway with WebSocket communication,
 * agent registration, discovery, and task delegation.
 */

import { WebSocket, WebSocketServer } from "ws";
import { createClient, RedisClientType } from "redis";

// ── Types ───────────────────────────────────────────────────────────────────

export interface AgentCard {
  id: string;
  name: string;
  type: string;
  tier: number;
  capabilities: string[];
  endpoint: string;
  status: "online" | "offline" | "busy";
  lastHeartbeat: string;
  metadata?: Record<string, unknown>;
}

export type MessageType = "ALERT" | "REQUEST" | "RESPONSE" | "DATA_UPDATE" | "EMERGENCY";
export type Priority = "CRITICAL" | "HIGH" | "NORMAL" | "LOW";

export interface A2AMessage {
  id: string;
  type: MessageType;
  priority: Priority;
  sourceAgentId: string;
  targetAgentId?: string;
  payload: Record<string, unknown>;
  timestamp: string;
  correlationId?: string;
}

export interface A2ATask {
  id: string;
  type: string;
  status: "pending" | "assigned" | "in_progress" | "completed" | "failed";
  priority: Priority;
  sourceAgentId: string;
  assignedAgentId?: string;
  payload: Record<string, unknown>;
  result?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

// ── Gateway Class ───────────────────────────────────────────────────────────

export class A2AGateway {
  private agents: Map<string, AgentCard> = new Map();
  private connections: Map<string, WebSocket> = new Map();
  private tasks: Map<string, A2ATask> = new Map();
  private redis: RedisClientType | null = null;

  async initRedis(redisUrl: string): Promise<void> {
    this.redis = createClient({ url: redisUrl }) as RedisClientType;
    this.redis.on("error", (err) => console.error("[A2A] Redis error:", err));
    await this.redis.connect();

    // Subscribe to inter-agent messaging channel
    const subscriber = this.redis.duplicate() as RedisClientType;
    await subscriber.connect();
    await subscriber.subscribe("a2a:messages", (message) => {
      const msg = JSON.parse(message) as A2AMessage;
      this.routeMessage(msg);
    });

    console.log("[A2A] Redis pub/sub initialized");
  }

  // ── Agent Registration ──────────────────────────────────────────────────

  registerAgent(card: AgentCard): void {
    this.agents.set(card.id, {
      ...card,
      status: "online",
      lastHeartbeat: new Date().toISOString(),
    });
    console.log(`[A2A] Agent registered: ${card.name} (${card.id})`);
  }

  unregisterAgent(agentId: string): void {
    this.agents.delete(agentId);
    this.connections.delete(agentId);
    console.log(`[A2A] Agent unregistered: ${agentId}`);
  }

  heartbeat(agentId: string): boolean {
    const agent = this.agents.get(agentId);
    if (!agent) return false;
    agent.lastHeartbeat = new Date().toISOString();
    agent.status = "online";
    return true;
  }

  // ── Agent Discovery ─────────────────────────────────────────────────────

  getAgent(agentId: string): AgentCard | undefined {
    return this.agents.get(agentId);
  }

  listAgents(): AgentCard[] {
    return Array.from(this.agents.values());
  }

  getAgentsByType(type: string): AgentCard[] {
    return this.listAgents().filter((a) => a.type === type);
  }

  getAgentsByTier(tier: number): AgentCard[] {
    return this.listAgents().filter((a) => a.tier === tier);
  }

  getDiscoveryDocument(): Record<string, unknown> {
    return {
      protocol: "A2A",
      version: "1.0",
      gateway: "eminence-healthos",
      agents: this.listAgents().map((a) => ({
        id: a.id,
        name: a.name,
        type: a.type,
        tier: a.tier,
        capabilities: a.capabilities,
        status: a.status,
      })),
      capabilities: [
        "agent_registration",
        "task_delegation",
        "message_routing",
        "heartbeat_monitoring",
      ],
    };
  }

  // ── WebSocket Management ────────────────────────────────────────────────

  registerConnection(agentId: string, ws: WebSocket): void {
    this.connections.set(agentId, ws);

    ws.on("close", () => {
      this.connections.delete(agentId);
      const agent = this.agents.get(agentId);
      if (agent) agent.status = "offline";
    });

    ws.on("message", (data) => {
      try {
        const message = JSON.parse(data.toString()) as A2AMessage;
        this.handleIncomingMessage(agentId, message);
      } catch (err) {
        console.error("[A2A] Invalid message from", agentId, err);
      }
    });
  }

  private handleIncomingMessage(sourceAgentId: string, message: A2AMessage): void {
    message.sourceAgentId = sourceAgentId;
    message.timestamp = new Date().toISOString();

    // Publish via Redis for distributed routing
    if (this.redis) {
      this.redis.publish("a2a:messages", JSON.stringify(message));
    } else {
      this.routeMessage(message);
    }
  }

  private routeMessage(message: A2AMessage): void {
    if (message.targetAgentId) {
      // Direct message to specific agent
      const ws = this.connections.get(message.targetAgentId);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    } else {
      // Broadcast to all connected agents (except sender)
      for (const [agentId, ws] of this.connections) {
        if (agentId !== message.sourceAgentId && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(message));
        }
      }
    }
  }

  // ── Task Delegation ─────────────────────────────────────────────────────

  createTask(task: Omit<A2ATask, "id" | "createdAt" | "updatedAt" | "status">): A2ATask {
    const now = new Date().toISOString();
    const fullTask: A2ATask = {
      ...task,
      id: `task_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      status: "pending",
      createdAt: now,
      updatedAt: now,
    };

    this.tasks.set(fullTask.id, fullTask);

    // Route task to appropriate agent
    const assignedAgent = this.findBestAgent(task.type, task.priority);
    if (assignedAgent) {
      fullTask.assignedAgentId = assignedAgent.id;
      fullTask.status = "assigned";
      assignedAgent.status = "busy";

      // Notify assigned agent
      const ws = this.connections.get(assignedAgent.id);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: "REQUEST",
            priority: task.priority,
            payload: { task: fullTask },
          })
        );
      }
    }

    return fullTask;
  }

  getTask(taskId: string): A2ATask | undefined {
    return this.tasks.get(taskId);
  }

  updateTaskStatus(
    taskId: string,
    status: A2ATask["status"],
    result?: Record<string, unknown>
  ): boolean {
    const task = this.tasks.get(taskId);
    if (!task) return false;

    task.status = status;
    task.updatedAt = new Date().toISOString();
    if (result) task.result = result;

    // Free up assigned agent
    if (status === "completed" || status === "failed") {
      if (task.assignedAgentId) {
        const agent = this.agents.get(task.assignedAgentId);
        if (agent) agent.status = "online";
      }
    }

    return true;
  }

  private findBestAgent(taskType: string, priority: Priority): AgentCard | undefined {
    const available = this.listAgents().filter(
      (a) => a.status === "online" && a.capabilities.includes(taskType)
    );

    if (available.length === 0) return undefined;

    // For critical tasks, prefer lower tier (more specialized) agents
    if (priority === "CRITICAL") {
      available.sort((a, b) => a.tier - b.tier);
    }

    return available[0];
  }
}
