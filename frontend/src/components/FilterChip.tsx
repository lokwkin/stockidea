import { X } from "lucide-react"
import type { Filter } from "@/types/stock"

interface FilterChipProps {
  filter: Filter
  onRemove: (id: number) => void
}

export function FilterChip({ filter, onRemove }: FilterChipProps) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1.5 font-mono text-xs">
      <span className="font-medium text-primary">{filter.displayName}</span>
      <span className="text-muted-foreground">{filter.operator}</span>
      <span>{String(filter.value)}</span>
      <button
        onClick={() => onRemove(filter.id)}
        className="flex h-4 w-4 items-center justify-center rounded-full bg-muted text-muted-foreground transition-colors hover:bg-destructive hover:text-white"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  )
}
