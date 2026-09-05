import { cn, confidenceColor } from "@/lib/utils";

interface ConfidenceBarProps {
  score: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function ConfidenceBar({
  score,
  showLabel = true,
  size = "md",
  className,
}: ConfidenceBarProps) {
  const pct = Math.round(score * 100);
  const color = confidenceColor(score);
  const heights = { sm: "h-1", md: "h-1.5", lg: "h-2" };

  return (
    <div className={cn("space-y-1", className)}>
      {showLabel && (
        <div className="flex justify-between items-center">
          <span className="text-[11px] text-[hsl(var(--text-muted))] font-medium">
            Confidence
          </span>
          <span
            className="text-[11px] font-semibold tabular-nums"
            style={{ color }}
          >
            {pct}%
          </span>
        </div>
      )}
      <div className={cn("confidence-bar", heights[size])}>
        <div
          className="confidence-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}
