"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Brain, Search, Cpu, Clock, Zap } from "lucide-react";
import { api, MemoryResult } from "@/lib/api";
import { ConfidenceBar } from "@/components/ui/ConfidenceBar";
import { timeAgo } from "@/lib/utils";

const MEMORY_TYPES = [
  { id: "working",    label: "Working",    color: "hsl(200 80% 55%)", desc: "Current task context" },
  { id: "episodic",   label: "Episodic",   color: "hsl(270 70% 60%)", desc: "Past experiences" },
  { id: "semantic",   label: "Semantic",   color: "hsl(142 70% 50%)", desc: "Knowledge & facts" },
  { id: "procedural", label: "Procedural", color: "hsl(35 90% 55%)",  desc: "How-to knowledge" },
  { id: "evidence",   label: "Evidence",   color: "hsl(220 100% 65%)", desc: "Source-backed facts" },
  { id: "reflection", label: "Reflection", color: "hsl(315 70% 60%)", desc: "Meta-patterns" },
];

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [results, setResults] = useState<MemoryResult[]>([]);

  const search = useMutation({
    mutationFn: () =>
      api.searchMemory({
        query,
        memory_types: selectedTypes.length > 0 ? selectedTypes : undefined,
        top_k: 20,
      }),
    onSuccess: (data) => setResults(data),
  });

  function toggleType(id: string) {
    setSelectedTypes((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  }

  return (
    <div className="p-6 space-y-5 fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Brain size={22} />
          Memory
        </h1>
        <p className="text-sm text-[hsl(var(--text-secondary))] mt-0.5">
          6-tier memory system with semantic retrieval
        </p>
      </div>

      {/* Memory type legend */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {MEMORY_TYPES.map((mt) => (
          <button
            key={mt.id}
            onClick={() => toggleType(mt.id)}
            className={`card p-3 text-left transition-all ${
              selectedTypes.includes(mt.id)
                ? "border-[hsl(var(--brand-primary)_/_0.6)] bg-[hsl(var(--brand-primary)_/_0.08)]"
                : ""
            }`}
          >
            <div
              className="w-2 h-2 rounded-full mb-2"
              style={{ background: mt.color }}
            />
            <p className="text-xs font-semibold">{mt.label}</p>
            <p className="text-[10px] text-[hsl(var(--text-muted))] mt-0.5">
              {mt.desc}
            </p>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-muted))]"
          />
          <input
            placeholder="Search memories semantically…"
            className="input pl-10"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && query && search.mutate()}
          />
        </div>
        <button
          className="btn btn-primary"
          onClick={() => search.mutate()}
          disabled={!query || search.isPending}
        >
          {search.isPending ? (
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Zap size={15} />
          )}
          Search
        </button>
      </div>

      {/* Scoring explanation */}
      <div className="card p-4 bg-[hsl(var(--surface-1))]">
        <p className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-2">
          Retrieval Scoring Formula
        </p>
        <div className="flex flex-wrap gap-2 text-[11px] font-mono text-[hsl(var(--text-muted))]">
          <span className="px-2 py-0.5 rounded bg-[hsl(var(--surface-3))]">0.45 × semantic similarity</span>
          <span>+</span>
          <span className="px-2 py-0.5 rounded bg-[hsl(var(--surface-3))]">0.20 × recency</span>
          <span>+</span>
          <span className="px-2 py-0.5 rounded bg-[hsl(var(--surface-3))]">0.15 × importance</span>
          <span>+</span>
          <span className="px-2 py-0.5 rounded bg-[hsl(var(--surface-3))]">0.10 × confidence</span>
          <span>+</span>
          <span className="px-2 py-0.5 rounded bg-[hsl(var(--surface-3))]">0.10 × access freq</span>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-[hsl(var(--text-secondary))]">
            {results.length} memories retrieved
          </p>
          {results.map((r) => {
            const mt = MEMORY_TYPES.find((t) => t.id === r.memory_type);
            return (
              <div key={r.memory_id} className="card p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span
                        className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full"
                        style={{
                          background: `${mt?.color ?? "#888"}20`,
                          color: mt?.color ?? "#888",
                          border: `1px solid ${mt?.color ?? "#888"}40`,
                        }}
                      >
                        {r.memory_type}
                      </span>
                      <span className="text-[10px] text-[hsl(var(--text-muted))]">
                        <Clock size={9} className="inline mr-0.5" />
                        {timeAgo(r.created_at)}
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed">{r.content}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-lg font-bold text-[hsl(var(--brand-primary))]">
                      {Math.round(r.score * 100)}
                    </div>
                    <div className="text-[9px] text-[hsl(var(--text-muted))] uppercase tracking-wider">
                      score
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <ConfidenceBar score={r.confidence} showLabel size="sm" />
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[11px] text-[hsl(var(--text-muted))] font-medium">Importance</span>
                      <span className="text-[11px] font-semibold">{Math.round(r.importance * 100)}%</span>
                    </div>
                    <div className="confidence-bar h-1">
                      <div
                        className="confidence-bar-fill bg-[hsl(var(--brand-secondary))]"
                        style={{ width: `${r.importance * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {search.isSuccess && results.length === 0 && (
        <div className="card p-10 text-center">
          <Cpu size={32} className="mx-auto mb-2 text-[hsl(var(--text-muted))]" />
          <p className="text-[hsl(var(--text-secondary))]">No memories found</p>
          <p className="text-xs text-[hsl(var(--text-muted))] mt-1">
            Agents populate memory as they process tasks
          </p>
        </div>
      )}
    </div>
  );
}
