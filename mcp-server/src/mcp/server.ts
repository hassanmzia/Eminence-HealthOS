/**
 * Eminence HealthOS — MCP Protocol Server
 * Node.js server implementing the Model Context Protocol (MCP/1.0)
 * with Redis caching, tool execution, and context provisioning.
 */

import { createServer, IncomingMessage, ServerResponse } from "http";
import { createClient, RedisClientType } from "redis";
import { buildMCPContext } from "./context";
import { MCP_TOOLS, executeTool, TOOL_MAP } from "./tools";
import type { MCPRequest, MCPResponse, MCPToolCall, MCPContext } from "./types";

// ── Configuration ───────────────────────────────────────────────────────────

const PORT = parseInt(process.env.MCP_PORT || "3100", 10);
const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379";

// Cache TTLs (seconds)
const CACHE_TTL = {
  patient: 300, // 5 minutes
  constraints: 600, // 10 minutes
  history: 7200, // 2 hours
} as const;

// ── Redis Client ────────────────────────────────────────────────────────────

let redis: RedisClientType;

async function initRedis(): Promise<void> {
  redis = createClient({ url: REDIS_URL }) as RedisClientType;
  redis.on("error", (err) => console.error("[MCP] Redis error:", err));
  await redis.connect();
  console.log("[MCP] Redis connected");
}

async function getCached<T>(key: string): Promise<T | null> {
  if (!redis) return null;
  const data = await redis.get(key);
  return data ? (JSON.parse(data) as T) : null;
}

async function setCache(key: string, value: unknown, ttl: number): Promise<void> {
  if (!redis) return;
  await redis.setEx(key, ttl, JSON.stringify(value));
}

// ── Request Parsing ─────────────────────────────────────────────────────────

function parseBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString()));
      } catch {
        reject(new Error("Invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}

function sendJSON(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function extractAuth(req: IncomingMessage): { tenantId: string; token: string } {
  const token = (req.headers.authorization || "").replace("Bearer ", "");
  const tenantId = (req.headers["x-tenant-id"] as string) || "";
  return { tenantId, token };
}

// ── MCP Protocol Handler ───────────────────────────────────────────────────

async function handleMCPRequest(
  request: MCPRequest,
  tenantId: string,
  token: string
): Promise<MCPResponse> {
  const { method, params, id } = request;

  switch (method) {
    // ── Context provisioning ──
    case "context/get": {
      const patientId = params.patientId as string;
      if (!patientId) {
        return { version: "1.0", error: { code: 400, message: "patientId required" }, id };
      }

      // Check cache
      const cacheKey = `mcp:context:${tenantId}:${patientId}`;
      const cached = await getCached<MCPContext>(cacheKey);
      if (cached) {
        return { version: "1.0", result: cached, id };
      }

      // Build fresh context
      const start = Date.now();
      const context = await buildMCPContext(patientId, tenantId, token);
      context.metadata.buildDuration = Date.now() - start;

      await setCache(cacheKey, context, CACHE_TTL.patient);

      return { version: "1.0", result: context, id };
    }

    // ── Tool listing ──
    case "tools/list": {
      return { version: "1.0", result: { tools: MCP_TOOLS }, id };
    }

    // ── Tool execution ──
    case "tools/call": {
      const toolCall: MCPToolCall = {
        tool: params.tool as string,
        arguments: (params.arguments || {}) as Record<string, unknown>,
        callId: (params.callId as string) || id,
      };

      if (!TOOL_MAP[toolCall.tool]) {
        return {
          version: "1.0",
          error: { code: 404, message: `Tool '${toolCall.tool}' not found` },
          id,
        };
      }

      const result = await executeTool(toolCall, tenantId, token);
      return { version: "1.0", result, id };
    }

    // ── Health check ──
    case "health": {
      return {
        version: "1.0",
        result: {
          status: "ok",
          redis: redis?.isOpen ?? false,
          tools: MCP_TOOLS.length,
          uptime: process.uptime(),
        },
        id,
      };
    }

    default:
      return {
        version: "1.0",
        error: { code: 404, message: `Unknown method: ${method}` },
        id,
      };
  }
}

// ── HTTP Server ─────────────────────────────────────────────────────────────

async function handleRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = req.url || "/";

  // Health endpoint
  if (req.method === "GET" && url === "/health") {
    sendJSON(res, 200, {
      status: "ok",
      service: "mcp-server",
      version: "1.0",
      redis: redis?.isOpen ?? false,
      tools: MCP_TOOLS.length,
    });
    return;
  }

  // Tools listing (convenience REST endpoint)
  if (req.method === "GET" && url === "/tools") {
    sendJSON(res, 200, { tools: MCP_TOOLS });
    return;
  }

  // MCP protocol endpoint
  if (req.method === "POST" && url === "/mcp") {
    const { tenantId, token } = extractAuth(req);

    try {
      const body = (await parseBody(req)) as unknown as MCPRequest;
      if (!body.method || !body.id) {
        sendJSON(res, 400, { error: "Invalid MCP request: method and id required" });
        return;
      }

      const response = await handleMCPRequest(
        { version: body.version || "1.0", method: body.method, params: body.params || {}, id: body.id },
        tenantId,
        token
      );

      sendJSON(res, response.error ? 400 : 200, response);
    } catch (error) {
      sendJSON(res, 500, {
        version: "1.0",
        error: {
          code: 500,
          message: error instanceof Error ? error.message : "Internal server error",
        },
      });
    }
    return;
  }

  sendJSON(res, 404, { error: "Not found" });
}

// ── Server Start ────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  try {
    await initRedis();
  } catch (error) {
    console.warn("[MCP] Redis unavailable, running without cache:", error);
  }

  const server = createServer(handleRequest);
  server.listen(PORT, () => {
    console.log(`[MCP] HealthOS MCP Server listening on port ${PORT}`);
    console.log(`[MCP] ${MCP_TOOLS.length} tools registered`);
  });
}

main().catch(console.error);
