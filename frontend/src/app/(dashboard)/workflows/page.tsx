"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Workflow, Search, ArrowRight, Clock } from "lucide-react";
import { api, Workflow as WFType } from "@/lib/api";
import { StatusBadge } from "@/components/ui/Badge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { timeAgo, fmtDate } from "@/lib/utils";
import Link from "next/link";
import { CreateWorkflowModal } from "@/components/workflows/CreateWorkflowModal";

export default function WorkflowsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => api.getWorkflows("page_size=50"),
    refetchInterval: 8_000,
  });

  const workflows = (data?.items ?? []).filter((w) => {
    const matchSearch =
      search === "" || w.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || w.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const STATUSES = ["all", "running", "completed", "failed", "pending", "cancelled"];

  return (
    <div className="p-6 space-y-5 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workflows</h1>
          <p className="text-sm text-[hsl(var(--text-secondary))] mt-0.5">
            {data?.total ?? 0} total workflows
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn btn-primary text-sm"
        >
          <Plus size={15} />
          New Workflow
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-muted))]"
          />
          <input
            placeholder="Search workflows…"
            className="input pl-9 py-2 text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1 flex-wrap">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === s
                  ? "bg-[hsl(var(--brand-primary))] text-white"
                  : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Workflow Table */}
      {isLoading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : workflows.length === 0 ? (
        <div className="card p-16 text-center">
          <Workflow size={40} className="mx-auto mb-3 text-[hsl(var(--text-muted))]" />
          <p className="font-medium text-[hsl(var(--text-secondary))]">
            No workflows found
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="btn btn-primary text-sm mt-4 mx-auto"
          >
            <Plus size={14} />
            Create your first workflow
          </button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[hsl(var(--border-subtle))]">
                {["Name", "Status", "Priority", "Created", "Duration", ""].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[hsl(var(--text-muted))]"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border-subtle))]">
              {workflows.map((wf) => (
                <WorkflowRow key={wf.id} wf={wf} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateWorkflowModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); refetch(); }}
        />
      )}
    </div>
  );
}

function WorkflowRow({ wf }: { wf: WFType }) {
  const duration = (() => {
    if (!wf.started_at) return "—";
    const end = wf.completed_at ? new Date(wf.completed_at) : new Date();
    const ms = end.getTime() - new Date(wf.started_at).getTime();
    if (ms < 60000) return `${Math.round(ms / 1000)}s`;
    return `${Math.round(ms / 60000)}m`;
  })();

  return (
    <tr className="hover:bg-[hsl(var(--surface-2))] transition-colors group">
      <td className="px-4 py-3">
        <div className="font-medium truncate max-w-[220px]">{wf.name}</div>
        {wf.description && (
          <div className="text-[11px] text-[hsl(var(--text-muted))] truncate max-w-[220px]">
            {wf.description}
          </div>
        )}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={wf.status} />
      </td>
      <td className="px-4 py-3">
        <span className="text-xs text-[hsl(var(--text-secondary))]">
          {wf.priority}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 text-xs text-[hsl(var(--text-muted))]">
          <Clock size={11} />
          {timeAgo(wf.created_at)}
        </div>
      </td>
      <td className="px-4 py-3">
        <span className="text-xs font-mono text-[hsl(var(--text-secondary))]">
          {duration}
        </span>
      </td>
      <td className="px-4 py-3">
        <Link
          href={`/workflows/${wf.id}`}
          className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-xs text-[hsl(var(--brand-primary))]"
        >
          View <ArrowRight size={12} />
        </Link>
      </td>
    </tr>
  );
}
