"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bot,
  Workflow,
  Activity,
  ShieldCheck,
  TrendingUp,
  Clock,
  Zap,
  AlertTriangle,
} from "lucide-react";
import { api, Agent, Workflow as WFType } from "@/lib/api";
import { StatusBadge } from "@/components/ui/Badge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { ConfidenceBar } from "@/components/ui/ConfidenceBar";
import { timeAgo, fmtMs } from "@/lib/utils";
import Link from "next/link";

export default function DashboardPage() {
  const { data: agentsData, isLoading: agentsLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.getAgents("page_size=100"),
    refetchInterval: 15_000,
  });

  const { data: workflowsData, isLoading: workflowsLoading } = useQuery({
    queryKey: ["workflows", "recent"],
    queryFn: () => api.getWorkflows("page_size=10"),
    refetchInterval: 10_000,
  });

  const { data: approvalsData } = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => api.getApprovals("pending"),
    refetchInterval: 10_000,
  });

  const agents = agentsData?.items ?? [];
  const workflows = workflowsData?.items ?? [];
  const pendingApprovals = approvalsData?.approvals ?? [];

  const healthyAgents = agents.filter((a) => a.status === "healthy").length;
  const unhealthyAgents = agents.filter(
    (a) => a.status === "unhealthy" || a.status === "offline"
  ).length;
  const runningWorkflows = workflows.filter((w) => w.status === "running").length;
  const completedToday = workflows.filter(
    (w) =>
      w.status === "completed" &&
      new Date(w.completed_at ?? "").toDateString() === new Date().toDateString()
  ).length;

  const avgReliability =
    agents.length > 0
      ? agents.reduce((s, a) => s + a.reliability_score, 0) / agents.length
      : 0;

  return (
    <div className="p-6 space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-[hsl(var(--text-secondary))] text-sm mt-0.5">
            AgentOS platform overview — real-time status
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="pulse-dot healthy" />
          <span className="text-sm text-[hsl(var(--text-secondary))]">
            Live
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon={<Bot size={18} />}
          label="Active Agents"
          value={healthyAgents}
          total={agents.length}
          sublabel={unhealthyAgents > 0 ? `${unhealthyAgents} unhealthy` : "All healthy"}
          color="brand"
          loading={agentsLoading}
        />
        <KpiCard
          icon={<Workflow size={18} />}
          label="Running Workflows"
          value={runningWorkflows}
          sublabel={`${completedToday} completed today`}
          color="accent"
          loading={workflowsLoading}
        />
        <KpiCard
          icon={<ShieldCheck size={18} />}
          label="Pending Approvals"
          value={pendingApprovals.length}
          sublabel={
            pendingApprovals.length > 0
              ? "Requires your attention"
              : "All clear"
          }
          color={pendingApprovals.length > 0 ? "warning" : "accent"}
          href="/approvals"
          loading={false}
        />
        <KpiCard
          icon={<TrendingUp size={18} />}
          label="Avg Reliability"
          value={`${Math.round(avgReliability * 100)}%`}
          sublabel="Across all agents"
          color="accent"
          loading={agentsLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent Health Panel */}
        <div className="lg:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-[15px]">Agent Fleet</h2>
            <Link
              href="/agents"
              className="text-xs text-[hsl(var(--brand-primary))] hover:underline"
            >
              View all →
            </Link>
          </div>
          {agentsLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          ) : agents.length === 0 ? (
            <EmptyState
              icon={<Bot size={32} />}
              message="No agents registered yet"
              sub="Start the agent workers to see them here"
            />
          ) : (
            <div className="space-y-2">
              {agents.slice(0, 8).map((agent) => (
                <AgentRow key={agent.agent_id} agent={agent} />
              ))}
              {agents.length > 8 && (
                <p className="text-xs text-[hsl(var(--text-muted))] text-center pt-1">
                  +{agents.length - 8} more agents
                </p>
              )}
            </div>
          )}
        </div>

        {/* Recent Workflows */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-[15px]">Recent Workflows</h2>
            <Link
              href="/workflows"
              className="text-xs text-[hsl(var(--brand-primary))] hover:underline"
            >
              View all →
            </Link>
          </div>
          {workflowsLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          ) : workflows.length === 0 ? (
            <EmptyState
              icon={<Workflow size={28} />}
              message="No workflows yet"
              sub="Create your first workflow to get started"
            />
          ) : (
            <div className="space-y-2">
              {workflows.map((wf) => (
                <WorkflowRow key={wf.id} workflow={wf} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Pending Approvals Alert */}
      {pendingApprovals.length > 0 && (
        <div className="card p-4 border-[hsl(35_90%_55%_/_0.4)] bg-[hsl(35_90%_55%_/_0.05)] slide-up">
          <div className="flex items-center gap-3">
            <AlertTriangle
              size={18}
              className="text-[hsl(35_90%_55%)] shrink-0"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">
                {pendingApprovals.length} approval
                {pendingApprovals.length > 1 ? "s" : ""} require your attention
              </p>
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5 truncate">
                {pendingApprovals
                  .slice(0, 2)
                  .map((a) => a.action)
                  .join(", ")}
                {pendingApprovals.length > 2 &&
                  ` and ${pendingApprovals.length - 2} more`}
              </p>
            </div>
            <Link href="/approvals" className="btn btn-ghost text-xs shrink-0">
              Review
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

// -------------------------------------------------------------------------
// Sub-components
// -------------------------------------------------------------------------
function KpiCard({
  icon,
  label,
  value,
  total,
  sublabel,
  color,
  href,
  loading,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  total?: number;
  sublabel: string;
  color: "brand" | "accent" | "warning" | "danger";
  href?: string;
  loading: boolean;
}) {
  const colorMap = {
    brand: "hsl(var(--brand-primary))",
    accent: "hsl(var(--brand-accent))",
    warning: "hsl(var(--brand-warning))",
    danger: "hsl(var(--brand-danger))",
  };
  const bgMap = {
    brand: "hsl(var(--brand-primary) / 0.12)",
    accent: "hsl(var(--brand-accent) / 0.12)",
    warning: "hsl(var(--brand-warning) / 0.12)",
    danger: "hsl(var(--brand-danger) / 0.12)",
  };

  const content = (
    <div className="metric-card flex items-start gap-4 h-full">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: bgMap[color], color: colorMap[color] }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[12px] text-[hsl(var(--text-secondary))] font-medium">
          {label}
        </p>
        {loading ? (
          <div className="shimmer h-8 w-16 rounded mt-1" />
        ) : (
          <div className="flex items-baseline gap-1.5">
            <span className="metric-value" style={{ color: colorMap[color] }}>
              {value}
            </span>
            {total !== undefined && (
              <span className="text-xs text-[hsl(var(--text-muted))]">
                / {total}
              </span>
            )}
          </div>
        )}
        <p className="text-[11px] text-[hsl(var(--text-muted))] mt-0.5">
          {sublabel}
        </p>
      </div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block hover:scale-[1.01] transition-transform">
        {content}
      </Link>
    );
  }
  return content;
}

function AgentRow({ agent }: { agent: Agent }) {
  return (
    <div className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-[hsl(var(--surface-2))] transition-colors group">
      <div
        className={`pulse-dot ${agent.status === "healthy" ? "healthy" : agent.status === "degraded" ? "running" : "unhealthy"} shrink-0`}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{agent.name}</span>
          <StatusBadge status={agent.status} dot={false} />
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-[11px] text-[hsl(var(--text-muted))] mono">
            v{agent.version}
          </span>
          <span className="text-[11px] text-[hsl(var(--text-muted))]">
            {agent.capabilities.slice(0, 2).join(", ")}
            {agent.capabilities.length > 2 && ` +${agent.capabilities.length - 2}`}
          </span>
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-xs font-semibold text-[hsl(var(--text-secondary))]">
          {Math.round(agent.reliability_score * 100)}%
        </div>
        {agent.avg_latency_ms && (
          <div className="text-[10px] text-[hsl(var(--text-muted))]">
            {fmtMs(agent.avg_latency_ms)}
          </div>
        )}
      </div>
    </div>
  );
}

function WorkflowRow({ workflow }: { workflow: WFType }) {
  const statusColors: Record<string, string> = {
    completed: "text-[hsl(var(--status-completed))]",
    running: "text-[hsl(var(--status-running))]",
    failed: "text-[hsl(var(--status-failed))]",
    pending: "text-[hsl(var(--status-pending))]",
    cancelled: "text-[hsl(var(--text-muted))]",
  };
  return (
    <Link
      href={`/workflows/${workflow.id}`}
      className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-[hsl(var(--surface-2))] transition-colors cursor-pointer"
    >
      <Zap
        size={14}
        className={statusColors[workflow.status] ?? "text-[hsl(var(--text-muted))]"}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{workflow.name}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <StatusBadge status={workflow.status} dot={false} />
          <span className="text-[10px] text-[hsl(var(--text-muted))]">
            {timeAgo(workflow.created_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}

function EmptyState({
  icon,
  message,
  sub,
}: {
  icon: React.ReactNode;
  message: string;
  sub: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="text-[hsl(var(--text-muted))] mb-3">{icon}</div>
      <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">
        {message}
      </p>
      <p className="text-xs text-[hsl(var(--text-muted))] mt-1">{sub}</p>
    </div>
  );
}
