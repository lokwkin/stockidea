import { useState, useMemo, useCallback } from "react"
import { ArrowUp, ArrowDown, Plus } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PercentBar } from "@/components/PercentBar"
import { FilterChip } from "@/components/FilterChip"
import { COLUMNS } from "@/config/columns"
import { cn } from "@/lib/utils"
import type {
  StockAnalysis,
  SortConfig,
  Filter,
  ColumnConfig,
} from "@/types/stock"

interface StockTableProps {
  data: StockAnalysis[]
}

const OPERATORS = [
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: ">=", label: "≥" },
  { value: "<=", label: "≤" },
  { value: "=", label: "=" },
  { value: "contains", label: "contains" },
]

function getCellValue(
  stock: StockAnalysis,
  column: ColumnConfig
): number | string | { count: number; total: number } {
  switch (column.key) {
    case "above_1w":
      return {
        count: stock.weeks_above_1_week_ago,
        total: Math.max(1, stock.total_weeks - 1),
      }
    case "above_2w":
      return {
        count: stock.weeks_above_2_weeks_ago,
        total: Math.max(1, stock.total_weeks - 2),
      }
    case "above_4w":
      return {
        count: stock.weeks_above_4_weeks_ago,
        total: Math.max(1, stock.total_weeks - 4),
      }
    default:
      return stock[column.key as keyof StockAnalysis]
  }
}

function getSortValue(stock: StockAnalysis, column: ColumnConfig): number | string {
  const value = getCellValue(stock, column)
  if (typeof value === "object" && "count" in value) {
    return value.total > 0 ? (value.count / value.total) * 100 : 0
  }
  return value as number | string
}

function formatValue(value: number, type: string, decimals = 2): string {
  console.log(value, type, decimals)
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

export function StockTable({ data }: StockTableProps) {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    column: null,
    direction: null,
  })
  const [filters, setFilters] = useState<Filter[]>([])
  const [filterColumn, setFilterColumn] = useState<string>(COLUMNS[0].key)
  const [filterOperator, setFilterOperator] = useState<string>(">")
  const [filterValue, setFilterValue] = useState<string>("")
  const [filterIdCounter, setFilterIdCounter] = useState(0)

  const selectedColumn = COLUMNS.find((c) => c.key === filterColumn)
  const isStringColumn = selectedColumn?.type === "string"

  const handleSort = useCallback((columnKey: string) => {
    setSortConfig((prev) => {
      if (prev.column === columnKey) {
        if (prev.direction === "asc") return { column: columnKey, direction: "desc" }
        if (prev.direction === "desc") return { column: null, direction: null }
      }
      return { column: columnKey, direction: "asc" }
    })
  }, [])

  const addFilter = useCallback(() => {
    if (!filterValue.trim()) return

    const column = COLUMNS.find((c) => c.key === filterColumn)
    if (!column) return

    const newFilter: Filter = {
      id: filterIdCounter,
      column: filterColumn as keyof StockAnalysis,
      operator: filterOperator as Filter["operator"],
      value: isStringColumn ? filterValue : parseFloat(filterValue),
      displayName: column.filterName,
    }

    setFilters((prev) => [...prev, newFilter])
    setFilterIdCounter((prev) => prev + 1)
    setFilterValue("")
  }, [filterColumn, filterOperator, filterValue, filterIdCounter, isStringColumn])

  const removeFilter = useCallback((id: number) => {
    setFilters((prev) => prev.filter((f) => f.id !== id))
  }, [])

  const clearFilters = useCallback(() => {
    setFilters([])
  }, [])

  const filteredAndSortedData = useMemo(() => {
    let result = [...data]

    // Apply filters
    for (const filter of filters) {
      const column = COLUMNS.find((c) => c.key === filter.column)
      if (!column) continue

      result = result.filter((stock) => {
        const rawValue = getSortValue(stock, column)

        if (column.type === "string") {
          const strValue = String(rawValue).toLowerCase()
          const filterStr = String(filter.value).toLowerCase()

          if (filter.operator === "contains") {
            return strValue.includes(filterStr)
          }
          if (filter.operator === "=") {
            return strValue === filterStr
          }
          return true
        }

        const numValue = typeof rawValue === "number" ? rawValue : parseFloat(String(rawValue))
        const filterNum = typeof filter.value === "number" ? filter.value : parseFloat(String(filter.value))

        switch (filter.operator) {
          case ">":
            return numValue > filterNum
          case "<":
            return numValue < filterNum
          case ">=":
            return numValue >= filterNum
          case "<=":
            return numValue <= filterNum
          case "=":
            return numValue === filterNum
          default:
            return true
        }
      })
    }

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
  }, [data, filters, sortConfig])

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      addFilter()
    }
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
      {/* Filter Section */}
      <div className="border-b border-border bg-muted/50 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-muted-foreground">Filter:</span>
          
          <Select value={filterColumn} onValueChange={(value) => {
            setFilterColumn(value)
            const col = COLUMNS.find((c) => c.key === value)
            setFilterOperator(col?.type === "string" ? "contains" : ">")
          }}>
            <SelectTrigger className="w-[160px] bg-background font-mono text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {COLUMNS.map((col) => (
                <SelectItem key={col.key} value={col.key} className="font-mono">
                  {col.filterName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filterOperator} onValueChange={setFilterOperator}>
            <SelectTrigger className="w-[100px] bg-background font-mono text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(isStringColumn
                ? OPERATORS.filter((o) => o.value === "contains" || o.value === "=")
                : OPERATORS.filter((o) => o.value !== "contains")
              ).map((op) => (
                <SelectItem key={op.value} value={op.value} className="font-mono">
                  {op.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Input
            type={isStringColumn ? "text" : "number"}
            step={isStringColumn ? undefined : "0.01"}
            placeholder="Value..."
            value={filterValue}
            onChange={(e) => setFilterValue(e.target.value)}
            onKeyDown={handleKeyPress}
            className="w-[120px] bg-background font-mono text-sm"
          />

          <Button onClick={addFilter} size="sm" className="gap-1">
            <Plus className="h-4 w-4" />
            Add Filter
          </Button>
        </div>

        {filters.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {filters.map((filter) => (
              <FilterChip key={filter.id} filter={filter} onRemove={removeFilter} />
            ))}
          </div>
        )}
      </div>

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
            {filteredAndSortedData.map((stock) => (
              <TableRow key={stock.symbol} className="border-b-border">
                {COLUMNS.map((column) => {
                  const value = getCellValue(stock, column)

                  if (column.type === "pct_bar" && typeof value === "object" && "count" in value) {
                    return (
                      <TableCell key={column.key} className="px-4 py-3">
                        <PercentBar count={value.count} total={value.total} />
                      </TableCell>
                    )
                  }

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
          Showing <strong className="text-primary">{filteredAndSortedData.length}</strong> of{" "}
          <strong className="text-primary">{data.length}</strong> stocks
        </span>
        {filters.length > 0 && (
          <Button variant="outline" size="sm" onClick={clearFilters}>
            Clear Filters
          </Button>
        )}
      </div>
    </div>
  )
}
