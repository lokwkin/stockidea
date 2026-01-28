import { useEffect, useState, useCallback, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { X, ArrowUp, ArrowDown, ExternalLink, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { AnalysisData, StockAnalysis } from "@/types/stock"
import { cn } from "@/lib/utils"
import { COLUMNS } from "@/config/columns"

type SortColumn = keyof StockAnalysis | null
type SortDirection = "asc" | "desc" | null

interface SortConfig {
  column: SortColumn
  direction: SortDirection
}

interface AnalysisPanelProps {
  symbol?: string
  analysisFile: string
  simulationRule: string
  involvedKeys?: string[]
  onClose: () => void
}

export function AnalysisPanel({ symbol, analysisFile, simulationRule, involvedKeys = [], onClose }: AnalysisPanelProps) {
  const navigate = useNavigate()
  const [data, setData] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rule, setRule] = useState<string>(simulationRule)
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    column: null,
    direction: null,
  })
  const [showColumnSelector, setShowColumnSelector] = useState(false)

  // Initialize visible columns with symbol + involvedKeys
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(() => {
    const initial = new Set<string>(["symbol"])
    involvedKeys.forEach(key => {
      if (key !== "symbol") {
        initial.add(key)
      }
    })
    return initial
  })

  // Update visible columns when involvedKeys changes
  useEffect(() => {
    setVisibleColumns(prev => {
      const updated = new Set(prev)
      // Always keep symbol
      updated.add("symbol")
      // Add all involved keys
      involvedKeys.forEach(key => {
        if (key !== "symbol") {
          updated.add(key)
        }
      })
      return updated
    })
  }, [involvedKeys])

  // Determine which columns to display based on user selection
  const displayColumns = useMemo(() => {
    return COLUMNS.filter(col => visibleColumns.has(col.key))
  }, [visibleColumns])

  const handleToggleColumn = useCallback((columnKey: string) => {
    // Prevent removing symbol
    if (columnKey === "symbol") return
    
    setVisibleColumns(prev => {
      const updated = new Set(prev)
      if (updated.has(columnKey)) {
        updated.delete(columnKey)
      } else {
        updated.add(columnKey)
      }
      return updated
    })
  }, [])

  // Update rule when simulationRule prop changes
  useEffect(() => {
    setRule(simulationRule)
  }, [simulationRule])

  // Load analysis data when analysisFile changes
  useEffect(() => {
    if (!analysisFile) return

    let cancelled = false

    requestAnimationFrame(() => {
      if (!cancelled) {
        setLoading(true)
        setError(null)
      }
    })

    const url = rule.trim()
      ? `/api/analysis/${analysisFile}?rule=${encodeURIComponent(rule.trim())}`
      : `/api/analysis/${analysisFile}`

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load analysis data")
        return res.json()
      })
      .then((json: AnalysisData) => {
        if (!cancelled) {
          setData(json)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [analysisFile, rule])

  const handleRuleSubmit = useCallback(() => {
    if (!analysisFile) return

    setLoading(true)
    setError(null)

    const url = rule.trim()
      ? `/api/analysis/${analysisFile}?rule=${encodeURIComponent(rule.trim())}`
      : `/api/analysis/${analysisFile}`

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load analysis data")
        return res.json()
      })
      .then((json: AnalysisData) => {
        setData(json)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
      }, [analysisFile, rule])

  // Use all data (filtered by rule), not just the selected symbol
  const filteredData = useMemo(() => {
    if (!data) return []
    return data.data
  }, [data])

  const handleSort = useCallback((columnKey: string) => {
    setSortConfig((prev): SortConfig => {
      const column = columnKey as keyof StockAnalysis
      if (prev.column === column) {
        if (prev.direction === "asc") return { column, direction: "desc" }
        if (prev.direction === "desc") return { column: null, direction: null }
      }
      return { column, direction: "asc" }
    })
  }, [])

  const sortedData = useMemo(() => {
    const result = [...filteredData]

    if (sortConfig.column && sortConfig.direction) {
      const column = COLUMNS.find((c) => c.key === sortConfig.column)
      if (column) {
        result.sort((a, b) => {
          let aVal: number | string | { count: number; total: number }
          let bVal: number | string | { count: number; total: number }

          // Handle special cases for percentage bars
          if (column.key === "above_1w") {
            aVal = {
              count: a.weeks_above_1_week_ago,
              total: Math.max(1, a.total_weeks - 1),
            }
            bVal = {
              count: b.weeks_above_1_week_ago,
              total: Math.max(1, b.total_weeks - 1),
            }
          } else if (column.key === "above_2w") {
            aVal = {
              count: a.weeks_above_2_weeks_ago,
              total: Math.max(1, a.total_weeks - 2),
            }
            bVal = {
              count: b.weeks_above_2_weeks_ago,
              total: Math.max(1, b.total_weeks - 2),
            }
          } else if (column.key === "above_4w") {
            aVal = {
              count: a.weeks_above_4_weeks_ago,
              total: Math.max(1, a.total_weeks - 4),
            }
            bVal = {
              count: b.weeks_above_4_weeks_ago,
              total: Math.max(1, b.total_weeks - 4),
            }
          } else {
            aVal = a[column.key as keyof StockAnalysis] as number | string
            bVal = b[column.key as keyof StockAnalysis] as number | string
          }

          // Handle percentage bar values
          if (typeof aVal === "object" && "count" in aVal && typeof bVal === "object" && "count" in bVal) {
            const aPct = aVal.total > 0 ? (aVal.count / aVal.total) * 100 : 0
            const bPct = bVal.total > 0 ? (bVal.count / bVal.total) * 100 : 0
            return sortConfig.direction === "asc" ? aPct - bPct : bPct - aPct
          }

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
  }, [filteredData, sortConfig])

  // Format functions
  const formatValue = (value: number, columnKey: string): string => {
    const column = COLUMNS.find((c) => c.key === columnKey)
    if (!column) return String(value)

    const decimals = column.decimals ?? 2

    if (column.type === "percent") {
      const sign = value >= 0 ? "+" : ""
      return `${sign}${value.toFixed(decimals)}%`
    }
    if (column.type === "r_squared") {
      return value.toFixed(decimals)
    }
    if (column.type === "number") {
      return decimals > 0 ? value.toFixed(decimals) : String(Math.round(value))
    }
    return String(value)
  }

  const getCellValue = (stock: StockAnalysis, columnKey: string): number | string | { count: number; total: number } => {
    if (columnKey === "above_1w") {
      return {
        count: stock.weeks_above_1_week_ago,
        total: Math.max(1, stock.total_weeks - 1),
      }
    }
    if (columnKey === "above_2w") {
      return {
        count: stock.weeks_above_2_weeks_ago,
        total: Math.max(1, stock.total_weeks - 2),
      }
    }
    if (columnKey === "above_4w") {
      return {
        count: stock.weeks_above_4_weeks_ago,
        total: Math.max(1, stock.total_weeks - 4),
      }
    }
    return stock[columnKey as keyof StockAnalysis] as number | string
  }

  return (
    <div className="fixed right-0 top-0 h-screen w-[600px] bg-card border-l shadow-2xl z-40 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-xl font-semibold">
          {symbol ? `Trend Analysis: ${symbol}` : "Trend Analysis"}
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const ruleParam = rule.trim() ? `?rule=${encodeURIComponent(rule.trim())}` : ""
              navigate(`/analysis/${analysisFile}${ruleParam}`)
            }}
            className="flex items-center gap-2"
          >
            <ExternalLink className="h-4 w-4" />
            View Full Data
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Analysis File Display */}
        <div>
          <label className="text-sm font-medium text-muted-foreground mb-1 block">
            Analysis File:
          </label>
          <div className="w-full rounded-md border border-input bg-muted px-3 py-2 text-sm">
            {analysisFile}
          </div>
        </div>

        {/* Rule Input */}
        <div>
          <label className="text-sm font-medium text-muted-foreground mb-1 block">
            Rule:
          </label>
          <div className="flex gap-2 items-start">
            <textarea
              value={rule}
              onChange={(e) => setRule(e.target.value)}
              placeholder="Enter rule expression"
              className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
              rows={3}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  handleRuleSubmit()
                }
              }}
            />
            <Button
              type="button"
              onClick={handleRuleSubmit}
              className="shrink-0"
              disabled={loading}
            >
              Apply
            </Button>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-4">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-muted-foreground">Loading analysis data...</p>
            </div>
          </div>
        ) : error ? (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
            <h3 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h3>
            <p className="text-muted-foreground">{error}</p>
          </div>
        ) : filteredData.length > 0 ? (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  {displayColumns.map((column) => {
                    const isNumeric = column.type === "number" || column.type === "percent" || column.type === "r_squared"
                    return (
                      <TableHead
                        key={column.key}
                        onClick={() => handleSort(column.key)}
                        className={cn(
                          "cursor-pointer select-none hover:bg-muted/50 transition-colors",
                          isNumeric && "text-right"
                        )}
                      >
                        <div className={cn("flex items-center gap-1", isNumeric && "justify-end")}>
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
                    )
                  })}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((stock) => (
                  <TableRow 
                    key={stock.symbol}
                    className={cn(symbol && stock.symbol === symbol && "bg-primary/10")}
                  >
                    {displayColumns.map((column) => {
                      const value = getCellValue(stock, column.key)
                      const isNumeric = column.type === "number" || column.type === "percent" || column.type === "r_squared"
                      
                      // Handle percentage bar values
                      if (typeof value === "object" && "count" in value) {
                        const percentage = value.total > 0 ? (value.count / value.total) * 100 : 0
                        return (
                          <TableCell key={column.key} className={cn(isNumeric && "text-right")}>
                            {percentage.toFixed(1)}%
                          </TableCell>
                        )
                      }
                      
                      // Handle string values (like symbol)
                      if (typeof value === "string") {
                        return (
                          <TableCell key={column.key} className={cn(column.key === "symbol" && "font-medium")}>
                            {value}
                          </TableCell>
                        )
                      }
                      
                      // Handle numeric values
                      return (
                        <TableCell key={column.key} className={cn(isNumeric && "text-right")}>
                          {formatValue(value, column.key)}
                        </TableCell>
                      )
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="rounded-lg border border-muted bg-muted/50 p-6 text-center">
            <p className="text-muted-foreground">
              No data found with the current rule.
            </p>
          </div>
        )}

        {/* Display Columns Section */}
        <div className="border-t pt-4 mt-4">
          <button
            onClick={() => setShowColumnSelector(!showColumnSelector)}
            className="flex w-full items-center justify-between text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <span>Display Columns</span>
            {showColumnSelector ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
          
          {showColumnSelector && (
            <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 max-h-64 overflow-y-auto">
              {COLUMNS.map((column) => {
                const isChecked = visibleColumns.has(column.key)
                const isSymbol = column.key === "symbol"
                
                return (
                  <label
                    key={column.key}
                    className={cn(
                      "flex items-center gap-1.5 px-1.5 py-0.5 rounded hover:bg-muted/50 cursor-pointer transition-colors text-xs",
                      isSymbol && "opacity-60"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => handleToggleColumn(column.key)}
                      disabled={isSymbol}
                      className="h-3 w-3 rounded border-input cursor-pointer disabled:cursor-not-allowed shrink-0"
                    />
                    <span className="flex-1 truncate">{column.displayName}</span>
                    {isSymbol && (
                      <span className="text-[10px] text-muted-foreground shrink-0">(req)</span>
                    )}
                  </label>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
