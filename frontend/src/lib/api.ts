const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Agents
  getAgents: (params?: string) =>
    apiFetch<{ items: Agent[]; total: number }>(`/agents?${params || ""}`),
  getAgent: (id: string) => apiFetch<Agent>(`/agents/${id}`),
  discoverAgents: (capability: string) =>
    apiFetch<Agent[]>(`/agents/discover/${capability}`),

  // Workflows
  getWorkflows: (params?: string) =>
    apiFetch<{ items: Workflow[]; total: number }>(`/workflows?${params || ""}`),
  getWorkflow: (id: string) => apiFetch<Workflow>(`/workflows/${id}`),
  createWorkflow: (data: CreateWorkflowRequest) =>
    apiFetch<{ workflow_id: string; status: string }>(`/workflows`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  cancelWorkflow: (id: string) =>
    apiFetch(`/workflows/${id}/cancel`, { method: "POST" }),

  // News
  getNewsEvents: () => apiFetch<{ events: NewsEvent[] }>(`/news/events`),
  getNewsEvent: (id: string) => apiFetch<NewsEvent>(`/news/events/${id}`),

  // Approvals
  getApprovals: (status = "pending") =>
    apiFetch<{ approvals: Approval[] }>(`/approvals?status=${status}`),
  decideApproval: (
    id: string,
    data: { decision: string; reviewer_id: string; reviewer_note?: string }
  ) => apiFetch(`/approvals/${id}/decide`, { method: "POST", body: JSON.stringify(data) }),

  // Memory
  searchMemory: (query: MemoryQuery) =>
    apiFetch<MemoryResult[]>(`/memory/search`, {
      method: "POST",
      body: JSON.stringify(query),
    }),

  // Health
  getHealth: () => apiFetch<HealthStatus>(`/health`),
};

// =========================================================================
// Types
// =========================================================================
export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  version: string;
  status: "healthy" | "degraded" | "unhealthy" | "offline";
  capabilities: string[];
  reliability_score: number;
  avg_latency_ms: number | null;
  circuit_breaker_state: "CLOSED" | "OPEN" | "HALF_OPEN";
  last_heartbeat: string | null;
  registered_at: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: "pending" | "planning" | "running" | "completed" | "failed" | "cancelled" | "paused";
  priority: string;
  graph: { nodes?: WorkflowNode[] };
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  trace_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowNode {
  node_id: string;
  capability: string;
  status: "pending" | "running" | "completed" | "failed";
  depends_on: string[];
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  goal?: string;
  input?: Record<string, unknown>;
  priority?: string;
  tenant_id?: string;
}

export interface NewsEvent {
  event_id: string;
  title: string;
  description: string;
  status: string;
  category: string;
  importance: number;
  article_ids: string[];
  timeline: TimelineEntry[];
  entities: NamedEntity[];
  first_seen: string;
  last_updated: string;
}

export interface TimelineEntry {
  timestamp: string;
  title: string;
  description: string;
  entry_type: string;
}

export interface NamedEntity {
  text: string;
  label: string;
}

export interface Approval {
  id: string;
  workflow_id: string;
  task_id: string;
  requested_by: string;
  action: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  reason: string;
  status: string;
  expires_at: string;
  created_at: string;
}

export interface MemoryQuery {
  query: string;
  tenant_id?: string;
  top_k?: number;
  memory_types?: string[];
}

export interface MemoryResult {
  memory_id: string;
  memory_type: string;
  content: string;
  score: number;
  confidence: number;
  importance: number;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  checks: Record<string, string>;
}
