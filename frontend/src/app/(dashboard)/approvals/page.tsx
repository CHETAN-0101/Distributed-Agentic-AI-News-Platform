"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, Check, X, Clock, AlertTriangle, Shield } from "lucide-react";
import { useState } from "react";
import { api, Approval } from "@/lib/api";
import { RiskBadge } from "@/components/ui/Badge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { timeAgo, fmtDate } from "@/lib/utils";

export default function ApprovalsPage() {
  const [tab, setTab] = useState<"pending" | "approved" | "rejected">("pending");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["approvals", tab],
    queryFn: () => api.getApprovals(tab),
    refetchInterval: tab === "pending" ? 5000 : 30000,
  });

  const decide = useMutation({
    mutationFn: ({ id, decision, note }: { id: string; decision: string; note?: string }) =>
      api.decideApproval(id, { decision, reviewer_id: "admin", reviewer_note: note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals"] });
    },
  });

  const approvals = data?.approvals ?? [];
  const pendingCount = approvals.filter((a) => a.status === "pending").length;

  return (
    <div className="p-6 space-y-5 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <ShieldCheck size={22} />
            Approvals
          </h1>
          <p className="text-sm text-[hsl(var(--text-secondary))] mt-0.5">
            Human-in-the-loop gates for high-risk agent actions
          </p>
        </div>
        {tab === "pending" && pendingCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[hsl(35_90%_55%_/_0.1)] border border-[hsl(35_90%_55%_/_0.3)]">
            <AlertTriangle size={14} className="text-[hsl(35_90%_55%)]" />
            <span className="text-sm font-medium text-[hsl(35_90%_55%)]">
              {pendingCount} requiring review
            </span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[hsl(var(--surface-2))] p-1 rounded-xl w-fit">
        {(["pending", "approved", "rejected"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
              tab === t
                ? "bg-[hsl(var(--surface-0))] text-[hsl(var(--text-primary))] shadow-sm"
                : "text-[hsl(var(--text-muted))] hover:text-[hsl(var(--text-secondary))]"
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : approvals.length === 0 ? (
        <div className="card p-16 text-center">
          <Shield size={40} className="mx-auto mb-3 text-[hsl(var(--text-muted))]" />
          <p className="font-medium text-[hsl(var(--text-secondary))]">
            {tab === "pending" ? "No pending approvals" : `No ${tab} approvals`}
          </p>
          {tab === "pending" && (
            <p className="text-sm text-[hsl(var(--text-muted))] mt-1">
              High-risk agent actions will appear here
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {approvals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onDecide={(decision, note) =>
                decide.mutate({ id: approval.id, decision, note })
              }
              deciding={decide.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ApprovalCard({
  approval,
  onDecide,
  deciding,
}: {
  approval: Approval;
  onDecide: (d: string, note?: string) => void;
  deciding: boolean;
}) {
  const [note, setNote] = useState("");
  const [showNoteField, setShowNoteField] = useState(false);
  const [pendingDecision, setPendingDecision] = useState<"approved" | "rejected" | null>(null);

  const isPending = approval.status === "pending";
  const isExpired = new Date(approval.expires_at) < new Date();

  function handleDecide(decision: "approved" | "rejected") {
    if (showNoteField) {
      onDecide(decision, note || undefined);
    } else {
      if (approval.risk_level === "CRITICAL" || approval.risk_level === "HIGH") {
        setPendingDecision(decision);
        setShowNoteField(true);
      } else {
        onDecide(decision);
      }
    }
  }

  return (
    <div
      className={`card p-5 space-y-4 ${
        isExpired ? "opacity-60" : ""
      } ${approval.risk_level === "CRITICAL" ? "border-red-900" : ""}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <RiskBadge risk={approval.risk_level} />
            {isExpired && (
              <span className="text-[10px] text-[hsl(var(--text-muted))] bg-[hsl(var(--surface-3))] px-2 py-0.5 rounded-full">
                Expired
              </span>
            )}
          </div>
          <h3 className="font-semibold text-sm leading-snug">{approval.action}</h3>
          <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 leading-relaxed">
            {approval.reason}
          </p>
        </div>
        {isPending && !isExpired && (
          <div className="flex flex-col items-end gap-1 shrink-0">
            <div className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-muted))]">
              <Clock size={10} />
              Expires {timeAgo(approval.expires_at)}
            </div>
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="flex flex-wrap gap-3 text-[11px] text-[hsl(var(--text-muted))]">
        <span>Requested by: <strong className="text-[hsl(var(--text-secondary))]">{approval.requested_by}</strong></span>
        {approval.workflow_id && (
          <span>Workflow: <strong className="text-[hsl(var(--text-secondary))] mono">{approval.workflow_id.slice(0, 8)}…</strong></span>
        )}
        <span>Submitted: {timeAgo(approval.created_at)}</span>
      </div>

      {/* Note field for high-risk */}
      {showNoteField && (
        <div className="space-y-2">
          <label className="text-xs font-medium text-[hsl(var(--text-secondary))]">
            Review note (optional for {pendingDecision === "approved" ? "approval" : "rejection"}):
          </label>
          <textarea
            className="input text-sm min-h-[60px] resize-none"
            placeholder="Add a note explaining your decision…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
      )}

      {/* Actions */}
      {isPending && !isExpired && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => handleDecide("rejected")}
            disabled={deciding}
            className="btn btn-danger flex-1 text-sm"
          >
            <X size={14} />
            {showNoteField && pendingDecision === "rejected" ? "Confirm Rejection" : "Reject"}
          </button>
          <button
            onClick={() => handleDecide("approved")}
            disabled={deciding}
            className="btn btn-primary flex-1 text-sm"
          >
            <Check size={14} />
            {showNoteField && pendingDecision === "approved" ? "Confirm Approval" : "Approve"}
          </button>
        </div>
      )}

      {!isPending && (
        <div className={`text-xs font-semibold px-3 py-2 rounded-lg ${
          approval.status === "approved"
            ? "bg-green-950/30 text-green-400"
            : "bg-red-950/30 text-red-400"
        }`}>
          {approval.status.charAt(0).toUpperCase() + approval.status.slice(1)}
        </div>
      )}
    </div>
  );
}
