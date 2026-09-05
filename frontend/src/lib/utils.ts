import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function timeAgo(date: string | null | undefined): string {
  if (!date) return "never";
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true });
  } catch {
    return "—";
  }
}

export function fmtDate(date: string | null | undefined): string {
  if (!date) return "—";
  try {
    return format(new Date(date), "MMM d, yyyy HH:mm");
  } catch {
    return "—";
  }
}

export function fmtMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function fmtScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function confidenceColor(score: number): string {
  if (score >= 0.8) return "hsl(142 70% 50%)";
  if (score >= 0.6) return "hsl(35 90% 55%)";
  return "hsl(0 75% 55%)";
}

export function statusClass(status: string): string {
  const map: Record<string, string> = {
    healthy: "badge-healthy",
    completed: "badge-completed",
    degraded: "badge-degraded",
    warning: "badge-warning",
    unhealthy: "badge-unhealthy",
    failed: "badge-failed",
    offline: "badge-offline",
    running: "badge-running",
    pending: "badge-pending",
    planning: "badge-pending",
    confirmed: "badge-confirmed",
    conflicting: "badge-conflicting",
    unverified: "badge-unverified",
  };
  return map[status?.toLowerCase()] ?? "badge-offline";
}

export function riskColor(risk: string): string {
  const map: Record<string, string> = {
    CRITICAL: "text-red-400 bg-red-950 border-red-800",
    HIGH: "text-orange-400 bg-orange-950 border-orange-800",
    MEDIUM: "text-yellow-400 bg-yellow-950 border-yellow-800",
    LOW: "text-green-400 bg-green-950 border-green-800",
  };
  return map[risk] ?? "text-slate-400";
}

export function truncate(str: string, max = 80): string {
  return str.length > max ? str.slice(0, max) + "…" : str;
}
