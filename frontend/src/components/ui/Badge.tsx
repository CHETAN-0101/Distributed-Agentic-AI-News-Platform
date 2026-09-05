import { cn, statusClass } from "@/lib/utils";

interface BadgeProps {
  status: string;
  label?: string;
  dot?: boolean;
  className?: string;
}

export function StatusBadge({ status, label, dot = true, className }: BadgeProps) {
  return (
    <span className={cn("badge", statusClass(status), className)}>
      {dot && (
        <span
          className="inline-block w-1.5 h-1.5 rounded-full"
          style={{ background: "currentColor", opacity: 0.8 }}
        />
      )}
      {label ?? status}
    </span>
  );
}

interface RiskBadgeProps {
  risk: string;
  className?: string;
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  const colors: Record<string, string> = {
    CRITICAL: "bg-red-950/50 text-red-400 border border-red-900",
    HIGH: "bg-orange-950/50 text-orange-400 border border-orange-900",
    MEDIUM: "bg-yellow-950/50 text-yellow-400 border border-yellow-900",
    LOW: "bg-green-950/50 text-green-400 border border-green-900",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider",
        colors[risk] ?? "bg-slate-900 text-slate-400",
        className
      )}
    >
      {risk}
    </span>
  );
}
