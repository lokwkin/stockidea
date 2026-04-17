import { useEffect, useState, useCallback, useRef, useMemo } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { Settings2 } from "lucide-react"
import { StockTable } from "@/components/StockTable"
import type { StockIndicators, IndicatorsDataAPI } from "@/types/stock"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { COLUMNS, DEFAULT_VISIBLE_COLUMNS } from "@/config/columns"
import { dateFormat, cn } from "@/lib/utils"

const DEFAULT_RANKING = "change_pct_13w / return_std_52w"

/** Group columns by their `group` field for the column picker */
function groupColumns() {
  const groups: Record<string, typeof COLUMNS> = {}
  for (const col of COLUMNS) {
    const g = col.group || "Other"
    if (!groups[g]) groups[g] = []
    groups[g].push(col)
  }
  return groups
}

const COLUMN_GROUPS = groupColumns()

export function AnalysisView() {
  const { date: urlDate } = useParams<{ date?: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [data, setData] = useState<{ date: string; data: StockIndicators[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDates, setLoadingDates] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState<string>("")
  const [rule, setRule] = useState<string>("")
  const [ranking, setRanking] = useState<string>("")
  const [maxStocks, setMaxStocks] = useState<string>("")
  // "applied" values are what's actually sent to the API. Inputs only update
  // these on Apply (button or Enter). Date + Index dropdowns refetch directly.
  const [appliedRule, setAppliedRule] = useState<string>("")
  const [appliedRanking, setAppliedRanking] = useState<string>("")
  const [appliedMaxStocks, setAppliedMaxStocks] = useState<string>("")
  const [stockIndex, setStockIndex] = useState<"SP500" | "NASDAQ">("SP500")
  const [symbolFilter, setSymbolFilter] = useState<string>("")
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(() => new Set(DEFAULT_VISIBLE_COLUMNS))
  const [columnPanelOpen, setColumnPanelOpen] = useState(false)
  const tableRef = useRef<HTMLDivElement>(null)

  const targetSymbol = searchParams.get("symbol")
  const urlRule = searchParams.get("rule")
  const urlRanking = searchParams.get("ranking")
  const urlMaxStocks = searchParams.get("max_stocks")
  const urlIndex = searchParams.get("index")

  // Load available dates on mount
  useEffect(() => {
    fetch("/api/indicators")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load indicator dates")
        return res.json()
      })
      .then((dates: string[]) => {
        if (dates.length === 0) {
          throw new Error("No indicator data available")
        }
        setAvailableDates(dates)
        if (urlDate && dates.includes(urlDate)) {
          setSelectedDate(urlDate)
        } else {
          setSelectedDate(dates[0])
          if (!urlDate || !dates.includes(urlDate)) {
            navigate(`/analysis/${dates[0]}`, { replace: true })
          }
        }
        setLoadingDates(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoadingDates(false)
      })
  }, [])

  // Handle URL date changes
  useEffect(() => {
    if (urlDate && availableDates.includes(urlDate) && selectedDate !== urlDate) {
      setSelectedDate(urlDate)
    }
  }, [urlDate, availableDates, selectedDate])

  // Set rule, ranking, max_stocks, index from URL query params on mount
  useEffect(() => {
    if (urlRule) {
      setRule(urlRule)
      setAppliedRule(urlRule)
    }
    if (urlRanking) {
      setRanking(urlRanking)
      setAppliedRanking(urlRanking)
    }
    if (urlMaxStocks) {
      setMaxStocks(urlMaxStocks)
      setAppliedMaxStocks(urlMaxStocks)
    }
    if (urlIndex === "SP500" || urlIndex === "NASDAQ") setStockIndex(urlIndex)
  }, [urlRule, urlRanking, urlMaxStocks, urlIndex])

  const buildIndicatorsUrl = useCallback(
    (
      date: string,
      ruleStr: string,
      rankingStr: string,
      maxStocksStr: string,
      indexStr: string
    ) => {
      const params = new URLSearchParams()
      const trimmedRule = ruleStr.trim()
      const trimmedRanking = rankingStr.trim()
      const trimmedMax = maxStocksStr.trim()
      if (trimmedRule) params.set("rule", trimmedRule)
      if (trimmedRanking) params.set("ranking", trimmedRanking)
      if (trimmedMax) {
        const n = parseInt(trimmedMax, 10)
        if (!isNaN(n) && n > 0) params.set("max_stocks", String(n))
      }
      if (indexStr && indexStr !== "SP500") params.set("index", indexStr)
      const qs = params.toString()
      return qs
        ? `/api/indicators/${date}/?${qs}`
        : `/api/indicators/${date}/`
    },
    []
  )

  // Load indicator data when selected date or rule changes
  useEffect(() => {
    if (!selectedDate) return

    let cancelled = false

    requestAnimationFrame(() => {
      if (!cancelled) {
        setLoading(true)
        setError(null)
      }
    })

    fetch(buildIndicatorsUrl(selectedDate, appliedRule, appliedRanking, appliedMaxStocks, stockIndex))
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load indicator data")
        return res.json()
      })
      .then((json: IndicatorsDataAPI) => {
        if (!cancelled) {
          setData({ date: json.date, data: json.data })
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
  }, [selectedDate, appliedRule, appliedRanking, appliedMaxStocks, stockIndex, buildIndicatorsUrl])

  // Scroll to target symbol when data loads
  useEffect(() => {
    if (!targetSymbol || !data || loading) return

    const timer = setTimeout(() => {
      if (tableRef.current) {
        const row = tableRef.current.querySelector(`[data-symbol="${targetSymbol}"]`) as HTMLElement
        if (row) {
          row.scrollIntoView({ behavior: "smooth", block: "center" })
          row.classList.add("bg-primary/10")
          setTimeout(() => {
            row.classList.remove("bg-primary/10")
          }, 2000)
        }
      }
    }, 100)

    return () => clearTimeout(timer)
  }, [targetSymbol, data, loading])

  const handleRuleSubmit = useCallback(() => {
    setAppliedRule(rule)
    setAppliedRanking(ranking)
    setAppliedMaxStocks(maxStocks)
  }, [rule, ranking, maxStocks])

  const toggleColumn = useCallback((key: string) => {
    setVisibleColumns((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        // Don't allow removing "symbol" — always visible
        if (key === "symbol") return prev
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }, [])

  const toggleGroup = useCallback((groupName: string) => {
    const groupCols = COLUMN_GROUPS[groupName]
    if (!groupCols) return

    setVisibleColumns((prev) => {
      const next = new Set(prev)
      const allVisible = groupCols.every((c) => next.has(c.key))
      for (const col of groupCols) {
        if (col.key === "symbol") continue
        if (allVisible) {
          next.delete(col.key)
        } else {
          next.add(col.key)
        }
      }
      return next
    })
  }, [])

  const resetColumns = useCallback(() => {
    setVisibleColumns(new Set(DEFAULT_VISIBLE_COLUMNS))
  }, [])

  const showAllColumns = useCallback(() => {
    setVisibleColumns(new Set(COLUMNS.map((c) => c.key)))
  }, [])

  const visibleCount = useMemo(() => visibleColumns.size, [visibleColumns])

  const filteredData = useMemo(() => {
    if (!data) return null
    const q = symbolFilter.trim().toUpperCase()
    if (!q) return data
    return {
      ...data,
      data: data.data.filter((s) => s.symbol.toUpperCase().includes(q)),
    }
  }, [data, symbolFilter])

  if (loadingDates) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading indicator dates...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
          <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
          <p className="text-muted-foreground">{error ?? "No data available"}</p>
          <p className="mt-4 text-sm text-muted-foreground">
            Make sure the API server is running and indicator data is available
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative flex">
      {/* Main content */}
      <div className={cn(
        "flex-1 px-4 py-8 sm:px-6 lg:px-8 transition-all duration-200",
        columnPanelOpen && "mr-64"
      )}>
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-start justify-between mb-2">
            <h1 className="text-3xl font-semibold tracking-tight text-foreground">
              Indicators
            </h1>
            <button
              onClick={() => setColumnPanelOpen(!columnPanelOpen)}
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors",
                columnPanelOpen
                  ? "border-primary bg-primary/5 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <Settings2 className="h-4 w-4" />
              Columns ({visibleCount})
            </button>
          </div>
          <p className="text-muted-foreground">
            Browse per-stock indicators with rule-based filtering and ranking
          </p>
        </header>

        {/* Date + Index — apply on change, no Apply button needed */}
        <div className="flex flex-wrap items-end gap-4 mb-6 max-w-3xl">
          <div className="space-y-2">
            <label htmlFor="date" className="text-sm font-medium">
              Date
            </label>
            <Select value={selectedDate} onValueChange={(value) => {
              setSelectedDate(value)
              const symbolParam = targetSymbol ? `?symbol=${targetSymbol}` : ""
              navigate(`/analysis/${value}${symbolParam}`)
            }}>
              <SelectTrigger id="date" className="w-[180px]">
                <SelectValue placeholder="Select a date" />
              </SelectTrigger>
              <SelectContent>
                {availableDates.map((date) => (
                  <SelectItem key={date} value={date}>
                    {date}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label htmlFor="index" className="text-sm font-medium">
              Stock Index
            </label>
            <Select
              value={stockIndex}
              onValueChange={(value) => setStockIndex(value as "SP500" | "NASDAQ")}
            >
              <SelectTrigger id="index" className="w-[160px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SP500">S&amp;P 500</SelectItem>
                <SelectItem value="NASDAQ">NASDAQ</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-6 space-y-6 mb-6 max-w-3xl">
          {/* Filter Rule */}
          <div className="space-y-2">
            <label htmlFor="rule" className="text-sm font-medium">
              Filter Rule
            </label>
            <textarea
              id="rule"
              value={rule}
              onChange={(e) => setRule(e.target.value)}
              placeholder="change_pct_13w > 10 AND max_drop_pct_2w < 15"
              className="flex min-h-[44px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
              rows={2}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  handleRuleSubmit()
                }
              }}
            />
            <p className="text-xs text-muted-foreground">
              Python expression evaluated against indicator fields. Leave empty to skip filtering.
            </p>
          </div>

          {/* Ranking + Max Stocks */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_180px]">
            <div className="space-y-2">
              <label htmlFor="ranking" className="text-sm font-medium">
                Ranking Expression
              </label>
              <Input
                id="ranking"
                value={ranking}
                onChange={(e) => setRanking(e.target.value)}
                placeholder={DEFAULT_RANKING}
                className="font-mono text-sm"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleRuleSubmit()
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Numeric formula — higher scores rank higher. Default: {DEFAULT_RANKING}
              </p>
            </div>
            <div className="space-y-2">
              <label htmlFor="max_stocks" className="text-sm font-medium">
                Max Stocks
              </label>
              <Input
                id="max_stocks"
                type="number"
                min="1"
                value={maxStocks}
                onChange={(e) => setMaxStocks(e.target.value)}
                placeholder="All"
                className="font-mono text-sm"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleRuleSubmit()
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Top N by ranking
              </p>
            </div>
          </div>

          {/* Apply — for rule / ranking / max stocks */}
          <div className="flex justify-end">
            <Button
              type="button"
              onClick={handleRuleSubmit}
              disabled={loading}
            >
              Apply
            </Button>
          </div>
        </div>

        {/* Symbol filter + table caption */}
        <div className="mb-3 flex items-center gap-3">
          <Input
            id="symbol_filter"
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            placeholder="Filter by symbol"
            className="w-48 font-mono text-sm uppercase"
          />
          {data && (
            <div className="text-sm text-muted-foreground">
              {dateFormat(data.date)} &middot;{" "}
              {filteredData && filteredData.data.length !== data.data.length
                ? `${filteredData.data.length} of ${data.data.length}`
                : data.data.length}{" "}
              stocks &middot; 52-week
            </div>
          )}
        </div>

        {/* Table */}
        <main>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-muted-foreground">Loading indicators...</p>
              </div>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
              <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
              <p className="text-muted-foreground">{error}</p>
            </div>
          ) : filteredData ? (
            <div ref={tableRef}>
              <StockTable
                data={filteredData.data}
                highlightedSymbol={targetSymbol || undefined}
                visibleColumns={visibleColumns}
              />
            </div>
          ) : null}
        </main>
      </div>

      {/* Column Picker Panel — fixed on the right */}
      {columnPanelOpen && (
        <div className="fixed right-0 top-0 h-screen w-64 border-l bg-background overflow-y-auto z-40 flex flex-col">
          <div className="sticky top-0 bg-background border-b px-4 py-3 flex items-center justify-between">
            <span className="text-sm font-semibold text-foreground">Columns</span>
            <div className="flex gap-2">
              <button
                onClick={resetColumns}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Reset
              </button>
              <button
                onClick={showAllColumns}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                All
              </button>
            </div>
          </div>

          <div className="px-3 py-2 space-y-3 flex-1">
            {Object.entries(COLUMN_GROUPS).map(([groupName, cols]) => {
              const allVisible = cols.every((c) => visibleColumns.has(c.key))
              const someVisible = cols.some((c) => visibleColumns.has(c.key))
              return (
                <div key={groupName}>
                  <button
                    onClick={() => toggleGroup(groupName)}
                    className="flex items-center gap-2 w-full text-left mb-1 group"
                  >
                    <div className={cn(
                      "h-4 w-4 rounded border flex items-center justify-center text-[10px]",
                      allVisible
                        ? "bg-primary border-primary text-primary-foreground"
                        : someVisible
                        ? "border-primary bg-primary/20"
                        : "border-muted-foreground/30"
                    )}>
                      {allVisible && "✓"}
                      {someVisible && !allVisible && "—"}
                    </div>
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider group-hover:text-foreground transition-colors">
                      {groupName}
                    </span>
                  </button>

                  <div className="space-y-0.5 ml-1">
                    {cols.map((col) => (
                      <label
                        key={col.key}
                        className="flex items-center gap-2 px-2 py-1 rounded-md cursor-pointer hover:bg-accent transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={visibleColumns.has(col.key)}
                          onChange={() => toggleColumn(col.key)}
                          disabled={col.key === "symbol"}
                          className="h-4 w-4 rounded border-input accent-primary cursor-pointer"
                        />
                        <span className="text-sm text-foreground">{col.displayName}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
