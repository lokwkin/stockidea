import { useState, useMemo, useCallback, memo } from "react"
import { ArrowUp, ArrowDown } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { COLUMNS } from "@/config/columns"
import { cn } from "@/lib/utils"
import type {
  StockMetrics,
  SortConfig,
  ColumnConfig,
} from "@/types/stock"

interface StockTableProps {
  data: StockMetrics[]
  highlightedSymbol?: string
}

function getCellValue(
  stock: StockMetrics,
  column: ColumnConfig
): number | string {
  return stock[column.key as keyof StockMetrics]
}

function getSortValue(stock: StockMetrics, column: ColumnConfig): number | string {
  return getCellValue(stock, column) as number | string
}

function formatValue(value: number, type: string, decimals = 2): string {
  if (type === "percent") {
    const sign = value > 0 ? "+" : ""
    return `${sign}${value.toFixed(decimals)}%`
  }
  if (type === "r_squared") {
    return value.toFixed(decimals)
  }
  if (type === "number") {
    return decimals > 0 ? value.toFixed(decimals) : String(Math.round(value))
  }
  return String(value)
}

function getValueColor(value: number, type: string): string {
  if (type === "percent") {
    if (value > 0) return "text-positive"
    if (value < 0) return "text-destructive"
    return "text-muted-foreground"
  }
  if (type === "r_squared") {
    if (value >= 0.7) return "text-positive"
    if (value >= 0.4) return "text-muted-foreground"
    return "text-destructive"
  }
  return ""
}

export const StockTable = memo(function StockTable({ data, highlightedSymbol }: StockTableProps) {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    column: null,
    direction: null,
  })

  const handleSort = useCallback((columnKey: string) => {
    setSortConfig((prev): SortConfig => {
      if (prev.column === columnKey) {
        if (prev.direction === "asc") return { column: columnKey as keyof StockMetrics, direction: "desc" }
        if (prev.direction === "desc") return { column: null, direction: null }
      }
      return { column: columnKey as keyof StockMetrics, direction: "asc" }
    })
  }, [])

  const sortedData = useMemo(() => {
    const result = [...data]

    // Apply sorting
    if (sortConfig.column && sortConfig.direction) {
      const column = COLUMNS.find((c) => c.key === sortConfig.column)
      if (column) {
        result.sort((a, b) => {
          const aVal = getSortValue(a, column)
          const bVal = getSortValue(b, column)

          if (typeof aVal === "string" && typeof bVal === "string") {
            return sortConfig.direction === "asc"
              ? aVal.localeCompare(bVal)
              : bVal.localeCompare(aVal)
          }

          const aNum = typeof aVal === "number" ? aVal : 0
          const bNum = typeof bVal === "number" ? bVal : 0

          return sortConfig.direction === "asc" ? aNum - bNum : bNum - aNum
        })
      }
    }

    return result
  }, [data, sortConfig])

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
      {/* Table */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-b-border hover:bg-transparent">
              {COLUMNS.map((column) => (
                <TableHead
                  key={column.key}
                  onClick={() => handleSort(column.key)}
                  className="cursor-pointer select-none whitespace-nowrap bg-muted/30 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                >
                  <div className="flex items-center gap-1">
                    {column.displayName}
                    {sortConfig.column === column.key && (
                      <span className="text-primary">
                        {sortConfig.direction === "asc" ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : (
                          <ArrowDown className="h-3 w-3" />
                        )}
                      </span>
                    )}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedData.map((stock) => (
              <TableRow
                key={stock.symbol}
                data-symbol={stock.symbol}
                className={cn(
                  "border-b-border",
                  highlightedSymbol === stock.symbol && "bg-primary/10 ring-2 ring-primary"
                )}
              >
                {COLUMNS.map((column) => {
                  const value = getCellValue(stock, column)

                  if (column.type === "string") {
                    return (
                      <TableCell
                        key={column.key}
                        className="px-4 py-3 font-semibold text-primary"
                      >
                        {value as string}
                      </TableCell>
                    )
                  }

                  const numValue = value as number
                  return (
                    <TableCell
                      key={column.key}
                      className={cn(
                        "px-4 py-3 font-mono text-sm",
                        getValueColor(numValue, column.type)
                      )}
                    >
                      {formatValue(numValue, column.type, column.decimals)}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Footer Stats */}
      <div className="flex items-center justify-between border-t border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        <span>
          Showing <strong className="text-primary">{sortedData.length}</strong> of{" "}
          <strong className="text-primary">{data.length}</strong> stocks
        </span>
      </div>
    </div>
  )
})
