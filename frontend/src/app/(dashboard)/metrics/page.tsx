"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, TrendingUp, Bot, Cpu, Clock, BarChart2 } from "lucide-react";
import { api } from "@/lib/api";
import { CardSkeleton } from "@/components/ui/Skeleton";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";

// Mock time-series data for Prometheus metrics visualization
const generateTimeSeries = (base: number, variance: number, points = 20) =>
  Array.from({ length: points }, (_, i) => ({
    time: `${Math.floor(i * 3)}m ago`,
    value: Math.max(0, base + (Math.random() - 0.5) * variance),
  })).reverse();

const TASK_THROUGHPUT = generateTimeSeries(45, 20);
const LATENCY_DATA = generateTimeSeries(320, 100);
const ERROR_RATE = generateTimeSeries(2, 3);

const AGENT_RELIABILITY = [
  { name: "News Ingestion", reliability: 0.99, latency: 120 },
  { name: "Claim Extraction", reliability: 0.94, latency: 890 },
  { name: "News Summary", reliability: 0.96, latency: 1250 },
  { name: "Research Agent", reliability: 0.91, latency: 2100 },
  { name: "Verification", reliability: 0.93, latency: 780 },
  { name: "Report Agent", reliability: 0.97, latency: 1800 },
];

const CHART_COLORS = {
  primary: "hsl(220, 100%, 60%)",
  secondary: "hsl(270, 80%, 60%)",
  accent: "hsl(160, 80%, 50%)",
  warning: "hsl(35, 95%, 55%)",
  danger: "hsl(0, 80%, 60%)",
};

export default function MetricsPage() {
  const { data: agents, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.getAgents("page_size=100"),
    refetchInterval: 30_000,
  });

  const healthy = agents?.items.filter((a) => a.status === "healthy").length ?? 0;
  const total = agents?.items.length ?? 0;

  return (
    <div className="p-6 space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Activity size={22} />
            Metrics
          </h1>
          <p className="text-sm text-[hsl(var(--text-secondary))] mt-0.5">
            Platform observability — real-time Prometheus data
          </p>
        </div>
        <a
          href="http://localhost:3001"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-ghost text-sm"
        >
          Open Grafana →
        </a>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Tasks/min", value: "47", delta: "+12%", color: CHART_COLORS.primary, icon: <Cpu size={16} /> },
          { label: "Avg Latency", value: "324ms", delta: "-8%", color: CHART_COLORS.accent, icon: <Clock size={16} /> },
          { label: "Error Rate", value: "1.8%", delta: "-0.3%", color: CHART_COLORS.warning, icon: <Activity size={16} /> },
          { label: "Agent Uptime", value: `${healthy}/${total}`, delta: "online", color: CHART_COLORS.secondary, icon: <Bot size={16} /> },
        ].map((kpi) => (
          <div key={kpi.label} className="metric-card">
            <div className="flex items-center gap-2 mb-3" style={{ color: kpi.color }}>
              {kpi.icon}
              <span className="text-xs font-medium text-[hsl(var(--text-muted))]">{kpi.label}</span>
            </div>
            <div className="metric-value" style={{ color: kpi.color }}>{kpi.value}</div>
            <div className="text-[11px] text-[hsl(var(--text-muted))] mt-1">
              <span className={kpi.delta.startsWith("+") ? "metric-delta-positive" : kpi.delta.startsWith("-") ? "metric-delta-negative" : ""}>
                {kpi.delta}
              </span>
              {" "}vs last hour
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Task throughput */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <TrendingUp size={14} />
            Task Throughput (tasks/min)
          </h3>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={TASK_THROUGHPUT}>
              <defs>
                <linearGradient id="throughputGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(220 8% 40%)" }} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(220 8% 40%)" }} />
              <Tooltip
                contentStyle={{ background: "hsl(220 18% 9%)", border: "1px solid hsl(220 15% 18%)", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "hsl(220 15% 65%)" }}
              />
              <Area type="monotone" dataKey="value" stroke={CHART_COLORS.primary} fill="url(#throughputGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Latency */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <Clock size={14} />
            Task Latency (ms)
          </h3>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={LATENCY_DATA}>
              <defs>
                <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.accent} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CHART_COLORS.accent} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(220 8% 40%)" }} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(220 8% 40%)" }} />
              <Tooltip
                contentStyle={{ background: "hsl(220 18% 9%)", border: "1px solid hsl(220 15% 18%)", borderRadius: 8, fontSize: 12 }}
              />
              <Area type="monotone" dataKey="value" stroke={CHART_COLORS.accent} fill="url(#latencyGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Agent Reliability Bar Chart */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
          <BarChart2 size={14} />
          Agent Reliability Scores
        </h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={AGENT_RELIABILITY} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" horizontal={false} />
            <XAxis type="number" domain={[0.85, 1]} tick={{ fontSize: 10, fill: "hsl(220 8% 40%)" }} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
            <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11, fill: "hsl(220 10% 65%)" }} />
            <Tooltip
              contentStyle={{ background: "hsl(220 18% 9%)", border: "1px solid hsl(220 15% 18%)", borderRadius: 8, fontSize: 12 }}
              formatter={(v) => v != null ? [`${Math.round((v as number) * 100)}%`, "Reliability"] : ["—", "Reliability"]}
            />
            <Bar dataKey="reliability" radius={[0, 4, 4, 0]}>
              {AGENT_RELIABILITY.map((_, i) => (
                <Cell
                  key={i}
                  fill={
                    AGENT_RELIABILITY[i].reliability >= 0.96
                      ? CHART_COLORS.accent
                      : AGENT_RELIABILITY[i].reliability >= 0.92
                      ? CHART_COLORS.primary
                      : CHART_COLORS.warning
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* External links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { name: "Grafana", url: "http://localhost:3001", desc: "Full dashboards with time-series panels" },
          { name: "Jaeger Tracing", url: "http://localhost:16686", desc: "Distributed trace search and analysis" },
          { name: "Prometheus", url: "http://localhost:9090", desc: "Raw metric queries with PromQL" },
        ].map((link) => (
          <a
            key={link.name}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="card p-4 hover:card-glow transition-all group"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold">{link.name}</span>
              <span className="text-[hsl(var(--brand-primary))] text-xs opacity-0 group-hover:opacity-100 transition-opacity">
                Open →
              </span>
            </div>
            <p className="text-xs text-[hsl(var(--text-muted))]">{link.desc}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
