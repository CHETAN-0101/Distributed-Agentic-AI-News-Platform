"use client";

import { useState } from "react";
import { X, Zap, FileText, Target } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

export function CreateWorkflowModal({ onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const EXAMPLE_GOALS = [
    "Analyze the latest AI news and produce an evidence-backed summary",
    "Research recent climate change developments and verify key claims",
    "Investigate cryptocurrency market movements and identify key factors",
  ];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !goal.trim()) return;

    setLoading(true);
    setError("");
    try {
      await api.createWorkflow({ name, goal, priority });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create workflow");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="glass-heavy rounded-2xl p-6 w-full max-w-lg relative z-10 scale-in shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 gradient-brand rounded-lg flex items-center justify-center">
              <Zap size={15} className="text-white" />
            </div>
            <div>
              <h2 className="font-bold text-base">New Workflow</h2>
              <p className="text-xs text-[hsl(var(--text-muted))]">
                Describe your goal — the Planner handles the rest
              </p>
            </div>
          </div>
          <button onClick={onClose} className="btn btn-ghost p-1.5">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] block mb-1.5">
              <FileText size={11} className="inline mr-1" />
              Workflow Name
            </label>
            <input
              type="text"
              placeholder="e.g. AI News Intelligence Report"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          {/* Goal */}
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] block mb-1.5">
              <Target size={11} className="inline mr-1" />
              Goal (natural language)
            </label>
            <textarea
              placeholder="Describe what you want the agents to accomplish…"
              className="input min-h-[100px] resize-none"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              required
            />

            {/* Example goals */}
            <div className="mt-2 space-y-1">
              <p className="text-[10px] text-[hsl(var(--text-muted))] font-medium">
                Examples:
              </p>
              {EXAMPLE_GOALS.map((eg) => (
                <button
                  key={eg}
                  type="button"
                  onClick={() => {
                    setGoal(eg);
                    if (!name) setName(eg.slice(0, 40));
                  }}
                  className="block w-full text-left text-[11px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] px-2 py-1 rounded hover:bg-[hsl(var(--surface-3))] transition-colors truncate"
                >
                  → {eg}
                </button>
              ))}
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] block mb-1.5">
              Priority
            </label>
            <div className="flex gap-2">
              {["LOW", "NORMAL", "HIGH", "CRITICAL"].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                    priority === p
                      ? "bg-[hsl(var(--brand-primary))] text-white border-transparent"
                      : "border-[hsl(var(--border-subtle))] text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border-medium))]"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary flex-1"
              disabled={loading || !name.trim() || !goal.trim()}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Planning…
                </span>
              ) : (
                "Launch Workflow"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
