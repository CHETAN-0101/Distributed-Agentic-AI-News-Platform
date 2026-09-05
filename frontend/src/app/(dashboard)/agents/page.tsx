"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Cpu, Clock, Shield, ChevronRight, Search } from "lucide-react";
import { useState } from "react";
import { api, Agent } from "@/lib/api";
import { StatusBadge } from "@/components/ui/Badge";
import { ConfidenceBar } from "@/components/ui/ConfidenceBar";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { timeAgo, fmtMs, truncate } from "@/lib/utils";

export default function AgentsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.getAgents("page_size=100"),
    refetchInterval: 15_000,
  });

  const agents = (data?.items ?? []).filter((a) => {
    const matchSearch =
      search === "" ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.capabilities.some((c) => c.includes(search.toLowerCase()));
    const matchStatus =
      statusFilter === "all" || a.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const counts = {
    all: data?.items.length ?? 0,
    healthy: data?.items.filter((a) => a.status === "healthy").length ?? 0,
    degraded: data?.items.filter((a) => a.status === "degraded").length ?? 0,
    unhealthy: data?.items.filter((a) => a.status === "unhealthy").length ?? 0,
  };

  return (
    <div className="p-6 space-y-5 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
          <p className="text-sm text-[hsl(var(--text-secondary))] mt-0.5">
            {counts.all} registered · {counts.healthy} healthy
          </p>
        </div>
        <button onClick={() => refetch()} className="btn btn-ghost text-sm">
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-muted))]"
          />
          <input
            type="text"
            placeholder="Search agents or capabilities…"
            className="input pl-9 py-2 text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          {(["all", "healthy", "degraded", "unhealthy"] as const).map(
            (s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === s
                    ? "bg-[hsl(var(--brand-primary))] text-white"
                    : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                }`}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}{" "}
                <span className="opacity-60">({counts[s as keyof typeof counts]})</span>
              </button>
            )
          )}
        </div>
      </div>

      {/* Agent Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : agents.length === 0 ? (
        <div className="card p-16 text-center">
          <Bot size={40} className="mx-auto mb-3 text-[hsl(var(--text-muted))]" />
          <p className="font-medium text-[hsl(var(--text-secondary))]">
            No agents found
          </p>
          <p className="text-sm text-[hsl(var(--text-muted))] mt-1">
            {search ? "Try a different search" : "Start agent workers to register them"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.agent_id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const circuitBreakerColor =
    agent.circuit_breaker_state === "OPEN"
      ? "text-red-400"
      : agent.circuit_breaker_state === "HALF_OPEN"
      ? "text-yellow-400"
      : "text-green-400";

  return (
    <div className="card p-5 space-y-4 slide-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className={`pulse-dot shrink-0 ${
              agent.status === "healthy"
                ? "healthy"
                : agent.status === "degraded"
                ? "running"
                : "unhealthy"
            }`}
          />
          <div className="min-w-0">
            <p className="font-semibold text-sm leading-tight truncate">
              {agent.name}
            </p>
            <p className="text-[10px] text-[hsl(var(--text-muted))] mono">
              v{agent.version}
            </p>
          </div>
        </div>
        <StatusBadge status={agent.status} dot={false} />
      </div>

      {/* Description */}
      {agent.description && (
        <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
          {truncate(agent.description, 90)}
        </p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <StatCell icon={<Clock size={11} />} label="Latency" value={fmtMs(agent.avg_latency_ms)} />
        <StatCell
          icon={<Shield size={11} />}
          label="Circuit"
          value={agent.circuit_breaker_state.replace("_", " ")}
          valueClass={circuitBreakerColor}
        />
      </div>

      {/* Reliability */}
      <ConfidenceBar
        score={agent.reliability_score}
        showLabel
        size="sm"
      />

      {/* Capabilities */}
      <div className="flex flex-wrap gap-1">
        {agent.capabilities.slice(0, 4).map((cap) => (
          <span
            key={cap}
            className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] mono"
          >
            {cap}
          </span>
        ))}
        {agent.capabilities.length > 4 && (
          <span className="text-[10px] text-[hsl(var(--text-muted))] px-1.5 py-0.5">
            +{agent.capabilities.length - 4}
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-[hsl(var(--border-subtle))]">
        <span className="text-[10px] text-[hsl(var(--text-muted))]">
          Last heartbeat {timeAgo(agent.last_heartbeat)}
        </span>
        <span className="text-[10px] text-[hsl(var(--text-muted))] mono">
          {agent.agent_id}
        </span>
      </div>
    </div>
  );
}

function StatCell({
  icon,
  label,
  value,
  valueClass = "text-[hsl(var(--text-primary))]",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="bg-[hsl(var(--surface-2))] rounded-lg px-3 py-2">
      <div className="flex items-center gap-1 text-[hsl(var(--text-muted))] mb-0.5">
        {icon}
        <span className="text-[10px] font-medium">{label}</span>
      </div>
      <span className={`text-xs font-semibold ${valueClass}`}>{value}</span>
    </div>
  );
}
