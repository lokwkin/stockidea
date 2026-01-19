import { cn } from "@/lib/utils"

interface PercentBarProps {
  count: number
  total: number
}

export function PercentBar({ count, total }: PercentBarProps) {
  const pct = total > 0 ? (count / total) * 100 : 0

  return (
    <span className="inline-flex items-center gap-2 font-mono text-xs">
      <span className="w-6 text-right">{count}</span>
      <span className="relative h-1.5 w-10 overflow-hidden rounded-full bg-muted">
        <span
          className={cn(
            "absolute inset-y-0 left-0 rounded-full transition-all duration-300",
            pct >= 50 ? "bg-positive" : "bg-muted-foreground/50"
          )}
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className="w-10 text-right text-muted-foreground">
        {pct.toFixed(0)}%
      </span>
    </span>
  )
}
