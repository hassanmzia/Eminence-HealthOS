/**
 * Eminence HealthOS — MCP Tool Definitions
 * Defines the 9 MCP tools available to agents via the MCP protocol.
 */

import type { MCPToolDefinition, MCPToolCall, MCPToolResult } from "./types";

// ── Tool Registry ───────────────────────────────────────────────────────────

export const MCP_TOOLS: MCPToolDefinition[] = [
  {
    name: "query_fhir_database",
    description:
      "Query patient FHIR R4 records. Supports Patient, Condition, Observation, " +
      "MedicationRequest, AllergyIntolerance, Encounter, CarePlan, DiagnosticReport, Procedure.",
    parameters: {
      type: "object",
      properties: {
        resourceType: { type: "string", description: "FHIR R4 resource type" },
        patientId: { type: "string", description: "Patient ID" },
        filters: {
          type: "object",
          description: "Optional FHIR search parameters",
        },
      },
      required: ["resourceType", "patientId"],
    },
  },
  {
    name: "query_graph_database",
    description:
      "Execute read-only Cypher queries against the Neo4j clinical knowledge graph. " +
      "Supports clinical relationships, drug interactions, disease pathways.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Cypher query (read-only, no WRITE/DELETE/MERGE)",
        },
        params: {
          type: "object",
          description: "Query parameters",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "vector_search",
    description:
      "Semantic search across Qdrant vector collections: guidelines, papers, " +
      "protocols, drugs, icd_codes, education.",
    parameters: {
      type: "object",
      properties: {
        collection: {
          type: "string",
          enum: [
            "guidelines",
            "papers",
            "protocols",
            "drugs",
            "icd_codes",
            "education",
          ],
          description: "Vector collection to search",
        },
        query: { type: "string", description: "Natural language search query" },
        topK: {
          type: "number",
          description: "Number of results (default: 5)",
        },
        filters: {
          type: "object",
          description: "Optional metadata filters",
        },
      },
      required: ["collection", "query"],
    },
  },
  {
    name: "check_drug_interactions",
    description:
      "Check for drug-drug interactions using the Neo4j knowledge graph. " +
      "Returns severity (contraindicated, major, moderate, minor) and management.",
    parameters: {
      type: "object",
      properties: {
        medications: {
          type: "array",
          items: { type: "string" },
          description: "List of medication RxNorm codes or names",
        },
        patientId: {
          type: "string",
          description: "Optional patient ID to include current medications",
        },
      },
      required: ["medications"],
    },
  },
  {
    name: "calculate_risk_score",
    description:
      "Execute ML risk models for a patient. Supports 8 risk types: " +
      "hospitalization, mortality, readmission, ed_visit, medication_adherence, " +
      "glucose_control, falls, sepsis.",
    parameters: {
      type: "object",
      properties: {
        patientId: { type: "string", description: "Patient ID" },
        riskType: {
          type: "string",
          enum: [
            "hospitalization",
            "mortality",
            "readmission",
            "ed_visit",
            "medication_adherence",
            "glucose_control",
            "falls",
            "sepsis",
          ],
          description: "Type of risk to calculate",
        },
      },
      required: ["patientId", "riskType"],
    },
  },
  {
    name: "send_notification",
    description:
      "Send multi-channel notifications (SMS, email, push, in-app) " +
      "to patients, physicians, nurses, or care teams.",
    parameters: {
      type: "object",
      properties: {
        recipientId: { type: "string", description: "Recipient user ID" },
        recipientType: {
          type: "string",
          enum: ["patient", "physician", "nurse", "care_team"],
        },
        channel: {
          type: "string",
          enum: ["sms", "email", "push", "in_app"],
        },
        priority: {
          type: "string",
          enum: ["critical", "high", "normal", "low"],
        },
        subject: { type: "string" },
        body: { type: "string" },
      },
      required: [
        "recipientId",
        "recipientType",
        "channel",
        "priority",
        "subject",
        "body",
      ],
    },
  },
  {
    name: "schedule_appointment",
    description:
      "Schedule a patient appointment. Supports 10 types: follow_up, " +
      "specialist_referral, lab_work, imaging, telehealth, urgent_care, " +
      "preventive, procedure, therapy, education.",
    parameters: {
      type: "object",
      properties: {
        patientId: { type: "string" },
        providerId: { type: "string" },
        appointmentType: {
          type: "string",
          enum: [
            "follow_up",
            "specialist_referral",
            "lab_work",
            "imaging",
            "telehealth",
            "urgent_care",
            "preventive",
            "procedure",
            "therapy",
            "education",
          ],
        },
        preferredDate: {
          type: "string",
          description: "ISO 8601 date",
        },
        urgency: {
          type: "string",
          enum: ["stat", "urgent", "routine"],
        },
        reason: { type: "string" },
        duration: {
          type: "number",
          description: "Duration in minutes",
        },
      },
      required: [
        "patientId",
        "providerId",
        "appointmentType",
        "urgency",
        "reason",
      ],
    },
  },
  {
    name: "find_hospital",
    description:
      "Find nearby healthcare facilities using geospatial PostGIS queries. " +
      "Supports filtering by specialty, insurance, and distance.",
    parameters: {
      type: "object",
      properties: {
        latitude: { type: "number" },
        longitude: { type: "number" },
        radiusMiles: {
          type: "number",
          description: "Search radius in miles (default: 25)",
        },
        specialty: { type: "string", description: "Medical specialty filter" },
        insurance: {
          type: "string",
          description: "Accepted insurance plan filter",
        },
      },
      required: ["latitude", "longitude"],
    },
  },
  {
    name: "nl2sql_query",
    description:
      "Convert natural language questions to SQL queries against the " +
      "clinical database. Returns structured results.",
    parameters: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "Natural language question about clinical data",
        },
        context: {
          type: "object",
          description:
            "Optional context (patient ID, date range) to constrain results",
        },
      },
      required: ["question"],
    },
  },
];

// ── Tool Name → Definition Lookup ───────────────────────────────────────────

export const TOOL_MAP: Record<string, MCPToolDefinition> = Object.fromEntries(
  MCP_TOOLS.map((t) => [t.name, t])
);

// ── Tool Executor ───────────────────────────────────────────────────────────

const BACKEND_URL = process.env.HEALTHOS_BACKEND_URL || "http://localhost:8000";

/**
 * Execute an MCP tool call by proxying to the backend API.
 */
export async function executeTool(
  call: MCPToolCall,
  tenantId: string,
  token: string
): Promise<MCPToolResult> {
  const start = Date.now();

  const toolDef = TOOL_MAP[call.tool];
  if (!toolDef) {
    return {
      callId: call.callId,
      tool: call.tool,
      success: false,
      result: null,
      error: `Unknown tool: ${call.tool}`,
      durationMs: Date.now() - start,
    };
  }

  // Validate read-only for graph queries
  if (call.tool === "query_graph_database") {
    const query = (call.arguments.query as string || "").toUpperCase();
    const writeOps = ["CREATE", "MERGE", "DELETE", "SET", "REMOVE", "DROP"];
    if (writeOps.some((op) => query.includes(op))) {
      return {
        callId: call.callId,
        tool: call.tool,
        success: false,
        result: null,
        error: "Write operations are not allowed in graph queries",
        durationMs: Date.now() - start,
      };
    }
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/mcp/tools/execute`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-ID": tenantId,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tool: call.tool,
        arguments: call.arguments,
        callId: call.callId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Tool execution failed: ${response.status}`);
    }

    const result = await response.json();

    return {
      callId: call.callId,
      tool: call.tool,
      success: true,
      result,
      durationMs: Date.now() - start,
    };
  } catch (error) {
    return {
      callId: call.callId,
      tool: call.tool,
      success: false,
      result: null,
      error: error instanceof Error ? error.message : String(error),
      durationMs: Date.now() - start,
    };
  }
}
