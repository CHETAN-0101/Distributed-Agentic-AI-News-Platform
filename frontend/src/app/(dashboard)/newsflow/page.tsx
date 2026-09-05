"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Newspaper,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  ChevronRight,
  Search,
  RefreshCw,
  Globe,
} from "lucide-react";
import { api, NewsEvent } from "@/lib/api";
import { StatusBadge } from "@/components/ui/Badge";
import { ConfidenceBar } from "@/components/ui/ConfidenceBar";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { timeAgo, fmtDate } from "@/lib/utils";

// MOCK data for demonstration when no real events exist
const MOCK_EVENTS: NewsEvent[] = [
  {
    event_id: "mock-1",
    title: "Global AI Governance Summit Produces Landmark Agreement",
    description:
      "Nations agree on foundational framework for AI oversight, though key enforcement mechanisms remain disputed.",
    status: "developing",
    category: "technology",
    importance: 0.92,
    article_ids: ["a1", "a2", "a3", "a4", "a5"],
    entities: [
      { text: "United Nations", label: "ORG" },
      { text: "OpenAI", label: "ORG" },
      { text: "EU", label: "ORG" },
    ],
    timeline: [
      {
        timestamp: new Date(Date.now() - 4 * 3600000).toISOString(),
        title: "Summit opens in Geneva",
        description: "35 nations convene to discuss AI governance",
        entry_type: "initial",
      },
      {
        timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
        title: "Draft framework circulated",
        description: "Draft governance principles published for review",
        entry_type: "update",
      },
      {
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        title: "Agreement signed by 28 nations",
        description: "7 nations withheld signature pending domestic review",
        entry_type: "official",
      },
    ],
    first_seen: new Date(Date.now() - 5 * 3600000).toISOString(),
    last_updated: new Date(Date.now() - 30 * 60000).toISOString(),
  },
  {
    event_id: "mock-2",
    title: "Federal Reserve Signals Unexpected Rate Path",
    description:
      "Fed Chair comments spark market volatility as traders reassess interest rate expectations.",
    status: "developing",
    category: "business",
    importance: 0.78,
    article_ids: ["b1", "b2", "b3"],
    entities: [
      { text: "Federal Reserve", label: "ORG" },
      { text: "Jerome Powell", label: "PERSON" },
      { text: "Wall Street", label: "GPE" },
    ],
    timeline: [
      {
        timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
        title: "Powell speaks at Jackson Hole",
        description: "Fed Chair delivers economic outlook remarks",
        entry_type: "initial",
      },
      {
        timestamp: new Date(Date.now() - 90 * 60000).toISOString(),
        title: "Markets react sharply",
        description: "S&P 500 drops 1.4% in afternoon trading",
        entry_type: "update",
      },
    ],
    first_seen: new Date(Date.now() - 3 * 3600000).toISOString(),
    last_updated: new Date(Date.now() - 45 * 60000).toISOString(),
  },
  {
    event_id: "mock-3",
    title: "Major Cybersecurity Breach Affects Global Logistics Networks",
    description:
      "Ransomware attack disrupts shipping operations across multiple ports; attribution disputed.",
    status: "developing",
    category: "technology",
    importance: 0.85,
    article_ids: ["c1", "c2", "c3", "c4"],
    entities: [
      { text: "CyberSec Group", label: "ORG" },
      { text: "Rotterdam Port", label: "GPE" },
      { text: "APT-29", label: "ORG" },
    ],
    timeline: [
      {
        timestamp: new Date(Date.now() - 8 * 3600000).toISOString(),
        title: "First reports of disruption",
        description: "Shipping systems go offline at multiple ports",
        entry_type: "initial",
      },
      {
        timestamp: new Date(Date.now() - 5 * 3600000).toISOString(),
        title: "Ransomware confirmed",
        description: "Security researchers confirm ransomware strain",
        entry_type: "update",
      },
      {
        timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
        title: "Attribution disputed",
        description: "US officials name APT group; Russia denies involvement",
        entry_type: "update",
      },
    ],
    first_seen: new Date(Date.now() - 9 * 3600000).toISOString(),
    last_updated: new Date(Date.now() - 20 * 60000).toISOString(),
  },
];

const MOCK_SUMMARIES: Record<string, { confirmed: string[]; conflicting: string[]; unknown: string[]; why_it_matters: string; confidence: number }> = {
  "mock-1": {
    confirmed: [
      "28 of 35 nations signed the AI governance framework",
      "Agreement establishes a new UN AI Safety Committee",
      "Mandatory incident reporting within 72 hours for AI systems above defined capability thresholds",
    ],
    conflicting: [
      "US and China dispute the scope of the enforcement mechanism",
      "Industry groups say thresholds are 'unworkable' while NGOs call them 'too loose'",
    ],
    unknown: [
      "Which 7 nations withheld signature and their specific objections",
      "Timeline for ratification in signatory nations",
      "Enforcement penalties and dispute resolution process",
    ],
    why_it_matters:
      "This represents the first multilateral binding framework on AI development, potentially reshaping how frontier models are developed and deployed globally.",
    confidence: 0.82,
  },
  "mock-2": {
    confirmed: [
      "Federal Reserve Chair spoke at Jackson Hole symposium",
      "S&P 500 declined 1.4% following remarks",
      "10-year Treasury yield rose 12 basis points",
    ],
    conflicting: [
      "Analysts disagree on whether comments signal a rate hike or pause",
      "Two Fed governors gave differing interpretations in subsequent interviews",
    ],
    unknown: [
      "Exact Fed decision at next September FOMC meeting",
      "Long-term impact on mortgage rates and consumer lending",
    ],
    why_it_matters:
      "Interest rate decisions directly affect borrowing costs for consumers and businesses, influencing everything from mortgages to corporate investment plans.",
    confidence: 0.74,
  },
  "mock-3": {
    confirmed: [
      "Ransomware attack confirmed affecting at least 6 major ports",
      "Shipping delays estimated at 72-96 hours for affected cargo",
      "Security firm CrowdStrike engaged for incident response",
    ],
    conflicting: [
      "Attribution: US officials say APT-29; independent researchers disagree",
      "Estimated financial impact ranges from $40M to $300M depending on source",
    ],
    unknown: [
      "Full scope of data exfiltration, if any",
      "Recovery timeline for all affected systems",
      "Whether other logistics networks are at risk",
    ],
    why_it_matters:
      "Critical infrastructure attacks on logistics networks can cascade into supply chain disruptions affecting global trade of goods worth billions.",
    confidence: 0.68,
  },
};

export default function NewsFlowPage() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<NewsEvent | null>(null);
  const [category, setCategory] = useState("all");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["news-events"],
    queryFn: () => api.getNewsEvents(),
    refetchInterval: 30_000,
  });

  const rawEvents = (data?.events ?? []).length > 0 ? data!.events : MOCK_EVENTS;

  const events = rawEvents.filter((e) => {
    const matchSearch =
      search === "" ||
      e.title.toLowerCase().includes(search.toLowerCase()) ||
      (e.description ?? "").toLowerCase().includes(search.toLowerCase());
    const matchCat = category === "all" || e.category === category;
    return matchSearch && matchCat;
  });

  const categories = ["all", ...Array.from(new Set(rawEvents.map((e) => e.category).filter(Boolean)))];

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="px-6 py-4 border-b border-[hsl(var(--border-subtle))] flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Newspaper size={18} className="text-[hsl(var(--brand-primary))]" />
          <h1 className="font-bold text-lg">NewsFlow AI</h1>
          <span className="text-xs text-[hsl(var(--text-muted))] bg-[hsl(var(--surface-2))] px-2 py-0.5 rounded-full">
            Evidence-backed intelligence
          </span>
        </div>
        <div className="flex-1" />
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-muted))]" />
          <input
            placeholder="Search events…"
            className="input pl-8 py-1.5 text-sm w-56"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button onClick={() => refetch()} className="btn btn-ghost text-sm p-2">
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Event list */}
        <div className="w-80 border-r border-[hsl(var(--border-subtle))] flex flex-col overflow-hidden">
          {/* Category filter */}
          <div className="px-3 py-2 flex gap-1 flex-wrap border-b border-[hsl(var(--border-subtle))]">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wider transition-all ${
                  category === cat
                    ? "bg-[hsl(var(--brand-primary))] text-white"
                    : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-muted))] hover:text-[hsl(var(--text-secondary))]"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="p-3 space-y-2">
                {[...Array(4)].map((_, i) => <CardSkeleton key={i} />)}
              </div>
            ) : events.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6">
                <Globe size={32} className="text-[hsl(var(--text-muted))] mb-2" />
                <p className="text-sm text-[hsl(var(--text-secondary))]">No events found</p>
                <p className="text-xs text-[hsl(var(--text-muted))] mt-1">
                  RSS feeds are being monitored
                </p>
              </div>
            ) : (
              events.map((event) => (
                <button
                  key={event.event_id}
                  onClick={() => setSelected(event)}
                  className={`w-full text-left px-4 py-3 border-b border-[hsl(var(--border-subtle))] transition-colors hover:bg-[hsl(var(--surface-2))] ${
                    selected?.event_id === event.event_id
                      ? "bg-[hsl(var(--brand-primary)_/_0.08)] border-l-2 border-l-[hsl(var(--brand-primary))]"
                      : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium leading-snug line-clamp-2 flex-1">
                      {event.title}
                    </p>
                    <ChevronRight size={12} className="text-[hsl(var(--text-muted))] shrink-0 mt-0.5" />
                  </div>
                  <div className="flex items-center gap-2 mt-1.5">
                    {event.category && (
                      <span className="text-[9px] font-semibold uppercase tracking-wider text-[hsl(var(--text-muted))] bg-[hsl(var(--surface-3))] px-1.5 py-0.5 rounded-full">
                        {event.category}
                      </span>
                    )}
                    <span className="text-[10px] text-[hsl(var(--text-muted))]">
                      {event.article_ids.length} sources · {timeAgo(event.last_updated)}
                    </span>
                  </div>
                  <div className="mt-2">
                    <ConfidenceBar score={event.importance} showLabel={false} size="sm" />
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Event detail */}
        <div className="flex-1 overflow-y-auto">
          {selected ? (
            <EventDetail event={selected} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-8">
              <Newspaper size={48} className="text-[hsl(var(--text-muted))] mb-4" />
              <h2 className="font-semibold text-lg text-[hsl(var(--text-secondary))]">
                Select an event
              </h2>
              <p className="text-sm text-[hsl(var(--text-muted))] mt-1 max-w-xs">
                Choose a news event from the left panel to see the evidence-backed analysis
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EventDetail({ event }: { event: NewsEvent }) {
  const summary = MOCK_SUMMARIES[event.event_id];

  return (
    <div className="p-6 space-y-6 max-w-3xl fade-in">
      {/* Title */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          {event.category && (
            <span className="text-[10px] font-semibold uppercase tracking-wider bg-[hsl(var(--brand-primary)_/_0.12)] text-[hsl(var(--brand-primary))] px-2 py-0.5 rounded-full">
              {event.category}
            </span>
          )}
          <span className="text-[10px] text-[hsl(var(--text-muted))]">
            {event.article_ids.length} sources · Updated {timeAgo(event.last_updated)}
          </span>
        </div>
        <h2 className="text-xl font-bold leading-tight">{event.title}</h2>
        {event.description && (
          <p className="text-[hsl(var(--text-secondary))] text-sm mt-2 leading-relaxed">
            {event.description}
          </p>
        )}
      </div>

      {/* Entities */}
      {event.entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {event.entities.map((e) => (
            <span
              key={e.text}
              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[hsl(var(--surface-2))] text-xs border border-[hsl(var(--border-subtle))]"
            >
              <span className="text-[9px] uppercase tracking-wider text-[hsl(var(--text-muted))]">
                {e.label}
              </span>
              <span className="font-medium">{e.text}</span>
            </span>
          ))}
        </div>
      )}

      {/* Evidence sections */}
      {summary && (
        <div className="space-y-4">
          {/* Confidence */}
          <div className="card p-4">
            <ConfidenceBar score={summary.confidence} showLabel size="md" />
          </div>

          {/* Confirmed */}
          <EvidenceSection
            icon={<CheckCircle size={15} />}
            title="Confirmed"
            type="confirmed"
            items={summary.confirmed}
            accent="hsl(142 70% 50%)"
            bg="hsl(142 70% 45% / 0.06)"
          />

          {/* Conflicting */}
          <EvidenceSection
            icon={<AlertTriangle size={15} />}
            title="Conflicting / Disputed"
            type="conflicting"
            items={summary.conflicting}
            accent="hsl(35 90% 55%)"
            bg="hsl(35 90% 55% / 0.06)"
          />

          {/* Unknown */}
          <EvidenceSection
            icon={<HelpCircle size={15} />}
            title="Unknown / Unverified"
            type="unknown"
            items={summary.unknown}
            accent="hsl(220 70% 60%)"
            bg="hsl(220 70% 60% / 0.06)"
          />

          {/* Why it matters */}
          <div className="card p-4 border-l-4 border-[hsl(var(--brand-secondary)_/_0.5)] bg-[hsl(var(--brand-secondary)_/_0.04)]">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--brand-secondary))] mb-2">
              Why It Matters
            </h3>
            <p className="text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
              {summary.why_it_matters}
            </p>
          </div>
        </div>
      )}

      {/* Timeline */}
      {event.timeline.length > 0 && (
        <div>
          <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
            <Clock size={14} />
            Timeline
          </h3>
          <div className="relative">
            <div className="absolute left-[7px] top-0 bottom-0 w-px bg-[hsl(var(--border-subtle))]" />
            <div className="space-y-4">
              {event.timeline.map((entry, i) => (
                <div key={i} className="flex gap-4 relative">
                  <div className="w-3.5 h-3.5 rounded-full bg-[hsl(var(--brand-primary))] shrink-0 ring-4 ring-[hsl(var(--surface-0))] z-10" />
                  <div className="flex-1 pb-1">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium leading-snug">{entry.title}</p>
                      <span className="text-[10px] text-[hsl(var(--text-muted))] whitespace-nowrap shrink-0">
                        {timeAgo(entry.timestamp)}
                      </span>
                    </div>
                    <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
                      {entry.description}
                    </p>
                    <span
                      className={`mt-1 inline-block text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full ${
                        entry.entry_type === "official"
                          ? "bg-green-950 text-green-400"
                          : entry.entry_type === "correction"
                          ? "bg-red-950 text-red-400"
                          : "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-muted))]"
                      }`}
                    >
                      {entry.entry_type}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EvidenceSection({
  icon,
  title,
  type,
  items,
  accent,
  bg,
}: {
  icon: React.ReactNode;
  title: string;
  type: string;
  items: string[];
  accent: string;
  bg: string;
}) {
  if (items.length === 0) return null;

  return (
    <div
      className="card p-4 border-l-4"
      style={{
        borderLeftColor: accent,
        background: bg,
        borderColor: `${accent}40`,
      }}
    >
      <div className="flex items-center gap-2 mb-3" style={{ color: accent }}>
        {icon}
        <h3 className="text-xs font-bold uppercase tracking-wider">{title}</h3>
        <span className="ml-auto text-xs opacity-70">{items.length}</span>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2.5 text-sm text-[hsl(var(--text-secondary))]">
            <span style={{ color: accent }} className="mt-0.5 shrink-0">
              •
            </span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
