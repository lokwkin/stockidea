import { useEffect, useState, useMemo, useCallback } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { Copy, Check, TrendingDown, TrendingUp, ExternalLink } from "lucide-react"
import type { Backtest } from "@/types/backtest"
import { BalanceChart } from "@/components/BalanceChart"
import { BacktestRebalanceDetailView } from "@/components/BacktestRebalanceDetailView"
import { BacktestInvestmentTable } from "@/components/BacktestInvestmentTable"
import { BacktestRebalanceTable } from "@/components/BacktestRebalanceTable"
import { AnalysisPanel } from "@/components/AnalysisPanel"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { dateFormat, cn } from "@/lib/utils"

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
}


export function BacktestView() {
  const { id: backtestId } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [backtestData, setBacktestData] = useState<Backtest | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [ruleCopied, setRuleCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tableView, setTableView] = useState<"investment" | "rebalance">("investment")
  const [selectedRebalanceIndex, setSelectedRebalanceIndex] = useState<number | null>(null)
  const [analysisPanelSymbol, setAnalysisPanelSymbol] = useState<string | undefined>(undefined)
  const [analysisPanelDate, setAnalysisPanelDate] = useState<string | null>(null)

  // Load backtest data when backtest ID changes
  useEffect(() => {
    if (!backtestId) {
      // If no ID in URL, redirect to first available backtest or show error
      fetch("/api/backtests")
        .then((res) => {
          if (!res.ok) throw new Error("Failed to load backtests list")
          return res.json()
        })
        .then((sims: Array<{ id: number }>) => {
          if (sims.length === 0) {
            setError("No backtests available")
            setLoading(false)
          } else {
            navigate(`/backtest/${sims[0].id}`, { replace: true })
          }
        })
        .catch((err) => {
          setError(err.message)
          setLoading(false)
        })
      return
    }

    let cancelled = false

    requestAnimationFrame(() => {
      if (!cancelled) {
        setLoading(true)
        setLoadingData(true)
        setError(null)
      }
    })

    fetch(`/api/backtests/${backtestId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load backtest data")
        return res.json()
      })
      .then((json: Backtest) => {
        if (!cancelled) {
          setBacktestData(json)
          setLoading(false)
          setLoadingData(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
          setLoadingData(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [backtestId, navigate])

  // Sync URL query param with selectedRebalanceIndex when backtestData loads or URL changes
  useEffect(() => {
    if (!backtestData) return

    const rebalanceDate = searchParams.get("rebalance")

    if (rebalanceDate) {
      // Find the index of the rebalance with matching date
      const index = backtestData.backtest_rebalance.findIndex((r) => r.date === rebalanceDate)
      if (index !== -1) {
        // Only update if different to avoid loops
        setSelectedRebalanceIndex((prev) => (prev !== index ? index : prev))
      } else {
        // Invalid date in URL, remove it
        const newSearchParams = new URLSearchParams(searchParams)
        newSearchParams.delete("rebalance")
        setSearchParams(newSearchParams, { replace: true })
        setSelectedRebalanceIndex(null)
      }
    } else {
      // URL has no rebalance param, clear selection if set
      setSelectedRebalanceIndex((prev) => (prev !== null ? null : prev))
    }
  }, [backtestData, searchParams, setSearchParams])

  const handleRebalanceSelect = useCallback(
    (index: number | null) => {
      setSelectedRebalanceIndex(index)

      // Update URL query param
      const newSearchParams = new URLSearchParams(searchParams)
      if (index !== null && backtestData) {
        const rebalance = backtestData.backtest_rebalance[index]
        if (rebalance) {
          newSearchParams.set("rebalance", rebalance.date)
        }
      } else {
        newSearchParams.delete("rebalance")
      }
      setSearchParams(newSearchParams)
    },
    [backtestData, searchParams, setSearchParams]
  )

  const handleCloseRebalance = useCallback(() => {
    setSelectedRebalanceIndex(null)
    // Remove rebalance query param from URL
    const newSearchParams = new URLSearchParams(searchParams)
    newSearchParams.delete("rebalance")
    setSearchParams(newSearchParams)
  }, [searchParams, setSearchParams])

  const handleCopyRule = useCallback(async () => {
    if (!backtestData?.rule_ref) return
    
    try {
      await navigator.clipboard.writeText(backtestData.rule_ref)
      setRuleCopied(true)
      setTimeout(() => setRuleCopied(false), 2000)
    } catch (err) {
      console.error("Failed to copy rule:", err)
    }
  }, [backtestData?.rule_ref])

  // Flatten all investments from all rebalances
  const allBacktestInvestments = useMemo(() => {
    if (!backtestData) return []
    return backtestData.backtest_rebalance.flatMap((rebalance) => rebalance.investments)
  }, [backtestData])

  // Calculate top 3 biggest losses and profits (sorted by percentage)
  const topLosses = useMemo(() => {
    if (!allBacktestInvestments.length) return []
    return [...allBacktestInvestments]
      .sort((a, b) => a.profit_pct - b.profit_pct)
      .slice(0, 3)
  }, [allBacktestInvestments])

  const topProfits = useMemo(() => {
    if (!allBacktestInvestments.length) return []
    return [...allBacktestInvestments]
      .sort((a, b) => b.profit_pct - a.profit_pct)
      .slice(0, 3)
  }, [allBacktestInvestments])

  const selectedRebalance = useMemo(() => {
    return selectedRebalanceIndex !== null && backtestData
      ? backtestData.backtest_rebalance[selectedRebalanceIndex]
      : null
  }, [selectedRebalanceIndex, backtestData])

  const totalProfit = useMemo(() => backtestData?.profit || 0, [backtestData])
  const totalProfitPct = useMemo(() => {
    return backtestData?.profit_pct ?? 0
  }, [backtestData])

  // Get backtest rule
  const backtestRule = useMemo(() => {
    if (!backtestData) return ""
    if (backtestData.backtest_config?.rule) {
      return backtestData.backtest_config.rule
    }
    if (backtestData.rule_ref) {
      return backtestData.rule_ref
    }
    return ""
  }, [backtestData])

  // Get involved keys from backtest config
  const involvedKeys = useMemo(() => {
    return backtestData?.backtest_config?.involved_keys || []
  }, [backtestData])

  const handleOpenAnalysis = useCallback((symbol: string, buyDate: string) => {
    // Find the rebalance that contains this investment by matching buy_date
    if (!backtestData) return
    
    const rebalance = backtestData.backtest_rebalance.find((r) =>
      r.investments.some((inv) => inv.symbol === symbol && inv.buy_date === buyDate)
    )
    
    if (rebalance) {
      // Use rebalance date to query indicators
      const indicatorsDate = rebalance.date.split("T")[0] // Ensure we only use the date part
      setAnalysisPanelSymbol(symbol)
      setAnalysisPanelDate(indicatorsDate)
    }
  }, [backtestData])

  const handleOpenAnalysisFromDate = useCallback((analysisDate: string) => {
    setAnalysisPanelSymbol(undefined)
    setAnalysisPanelDate(analysisDate)
  }, [])

  const handleCloseAnalysis = useCallback(() => {
    setAnalysisPanelSymbol(undefined)
    setAnalysisPanelDate(null)
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading backtests...</p>
        </div>
      </div>
    )
  }

  if (error && !backtestData) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
          <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
          <p className="text-muted-foreground">{error ?? "No data available"}</p>
          <p className="mt-4 text-sm text-muted-foreground">
            Make sure the API server is running and backtest data is available
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      <div className={cn(
        "relative mx-auto max-w-[2000px] px-4 py-8 sm:px-6 lg:px-8 transition-all duration-300",
        analysisPanelDate && "mr-[600px]"
      )}>
        {/* Header */}
        <header className="mb-8">
          <div className="mb-6 text-center">
            <h1 className="mb-4 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
              Backtest Results
            </h1>
            {backtestId && (
              <p className="text-muted-foreground font-mono text-sm">ID: {backtestId}</p>
            )}
          </div>

          {/* Backtest Summary */}
          {backtestData && (
            <div className="mx-auto max-w-6xl">
              <div className="rounded-lg border bg-card p-6 shadow-sm">
                <div className="mb-6 flex items-center justify-between">
                  <h2 className="text-2xl font-semibold">Backtest Summary</h2>
                  <Button
                    variant="outline"
                    onClick={() => {
                      if (!backtestData?.backtest_config) return
                      const config = backtestData.backtest_config
                      // Convert dates from ISO to yyyy/mm/dd format for URL
                      const dateStart = dateFormat(config.date_start).replace(/-/g, "/")
                      const dateEnd = dateFormat(config.date_end).replace(/-/g, "/")
                      
                      const params = new URLSearchParams({
                        max_stocks: config.max_stocks.toString(),
                        rebalance_interval_weeks: config.rebalance_interval_weeks.toString(),
                        date_start: dateStart,
                        date_end: dateEnd,
                        rule: config.rule,
                        index: config.index,
                      })
                      
                      navigate(`/backtest/create?${params.toString()}`)
                    }}
                    className="flex items-center gap-2"
                  >
                    <Copy className="h-4 w-4" />
                    Clone Backtest
                  </Button>
                </div>
                
                {/* Period and Performance */}
                <div className="mb-6 grid grid-cols-1 gap-6 border-b pb-6 md:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Period</p>
                    <p className="text-base font-medium">
                      {dateFormat(backtestData.date_start)} - {dateFormat(backtestData.date_end)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Initial Balance</p>
                    <p className="text-base font-medium">{formatCurrency(backtestData.initial_balance)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Final Balance</p>
                    <p className="text-base font-medium">
                      {formatCurrency(backtestData.final_balance)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Total Return</p>
                    <p className={`text-base font-semibold ${totalProfitPct >= 0 ? "text-green-600" : "text-red-600"}`}>
                      {formatPercent(totalProfitPct)}
                    </p>
                    <p className={`text-sm ${totalProfitPct >= 0 ? "text-green-600" : "text-red-600"}`}>
                      {formatCurrency(totalProfit)}
                    </p>
                  </div>
                </div>

                {/* Configuration */}
                <div>
                  <h3 className="mb-4 text-lg font-semibold">Configuration</h3>
                  {backtestData.backtest_config ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">Stock Index</p>
                          <p className="text-base font-medium">{backtestData.backtest_config.index}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">Max Stocks</p>
                          <p className="text-base font-medium">{backtestData.backtest_config.max_stocks}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">Rebalance Interval</p>
                          <p className="text-base font-medium">{backtestData.backtest_config.rebalance_interval_weeks} weeks</p>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground mb-2">Selection Rule</p>
                        <div className="flex gap-2 items-start">
                          <textarea
                            readOnly
                            value={backtestData.backtest_config.rule}
                            className="flex min-h-[60px] w-full rounded-md border border-input bg-muted px-3 py-2 text-sm font-mono shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                            rows={Math.min(Math.max(backtestData.backtest_config.rule.split('\n').length, 2), 6)}
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={async () => {
                              try {
                                await navigator.clipboard.writeText(backtestData.backtest_config!.rule)
                                setRuleCopied(true)
                                setTimeout(() => setRuleCopied(false), 2000)
                              } catch (err) {
                                console.error("Failed to copy rule:", err)
                              }
                            }}
                            className="shrink-0"
                            title="Copy rule to clipboard"
                          >
                            {ruleCopied ? (
                              <Check className="h-4 w-4 text-green-600" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : backtestData.rule_ref ? (
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Selection Rule</p>
                      <div className="flex gap-2 items-start">
                        <textarea
                          readOnly
                          value={backtestData.rule_ref}
                          className="flex min-h-[60px] w-full rounded-md border border-input bg-muted px-3 py-2 text-sm font-mono shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                          rows={Math.min(Math.max(backtestData.rule_ref.split('\n').length, 2), 6)}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={handleCopyRule}
                          className="shrink-0"
                          title="Copy rule to clipboard"
                        >
                          {ruleCopied ? (
                            <Check className="h-4 w-4 text-green-600" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </header>

        {/* Main Content */}
        <main className="space-y-8">
          {loadingData ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-muted-foreground">Loading backtest data...</p>
              </div>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
              <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
              <p className="text-muted-foreground">{error}</p>
            </div>
          ) : backtestData ? (
            <>
              {/* Balance History Chart */}
              <BalanceChart
                backtestData={backtestData}
                selectedRebalanceIndex={selectedRebalanceIndex}
                onRebalanceSelect={handleRebalanceSelect}
                formatDate={dateFormat}
                formatCurrency={formatCurrency}
                formatPercent={formatPercent}
              />

              {/* Selected Rebalance Detail Section */}
              {selectedRebalance && (
                <BacktestRebalanceDetailView
                  rebalance={selectedRebalance}
                  formatDate={dateFormat}
                  formatCurrency={formatCurrency}
                  formatPercent={formatPercent}
                  onClose={handleCloseRebalance}
                  onOpenAnalysis={handleOpenAnalysisFromDate}
                />
              )}

              {/* Top Losses and Profits */}
              {(topLosses.length > 0 || topProfits.length > 0) && (
                <div className="rounded-lg border bg-card p-6">
                  <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                    {/* Top Losses */}
                    <div>
                      <div className="mb-3 flex items-center gap-2">
                        <TrendingDown className="h-5 w-5 text-red-600" />
                        <h3 className="text-lg font-semibold">Biggest Losses</h3>
                      </div>
                      <div className="space-y-3">
                        {topLosses.map((investment, idx) => (
                          <div
                            key={`loss-${investment.symbol}-${investment.buy_date}`}
                            className="rounded-lg border border-red-200 bg-red-50/50 p-4 dark:border-red-900 dark:bg-red-950/20"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1">
                                <div className="mb-1 flex items-center gap-2">
                                  <Badge variant="destructive" className="text-xs">
                                    #{idx + 1}
                                  </Badge>
                                  <span className="font-semibold">{investment.symbol}</span>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  {dateFormat(investment.buy_date)} → {dateFormat(investment.sell_date)}
                                </p>
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="text-right">
                                  <p className="text-sm font-semibold text-red-600">
                                    {formatPercent(investment.profit_pct)}
                                  </p>
                                  <p className="text-xs text-red-600">
                                    {formatCurrency(investment.profit)}
                                  </p>
                                </div>
                                <Button
                                  variant="outline"
                                  size="icon"
                                  className="h-8 w-8 shrink-0"
                                  onClick={() => handleOpenAnalysis(investment.symbol, investment.buy_date)}
                                  title={`View ${investment.symbol} analysis`}
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Top Profits */}
                    <div>
                      <div className="mb-3 flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-green-600" />
                        <h3 className="text-lg font-semibold">Biggest Profits</h3>
                      </div>
                      <div className="space-y-3">
                        {topProfits.map((investment, idx) => (
                          <div
                            key={`profit-${investment.symbol}-${investment.buy_date}`}
                            className="rounded-lg border border-green-200 bg-green-50/50 p-4 dark:border-green-900 dark:bg-green-950/20"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1">
                                <div className="mb-1 flex items-center gap-2">
                                  <Badge variant="default" className="bg-green-600 text-xs">
                                    #{idx + 1}
                                  </Badge>
                                  <span className="font-semibold">{investment.symbol}</span>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  {dateFormat(investment.buy_date)} → {dateFormat(investment.sell_date)}
                                </p>
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="text-right">
                                  <p className="text-sm font-semibold text-green-600">
                                    {formatPercent(investment.profit_pct)}
                                  </p>
                                  <p className="text-xs text-green-600">
                                    {formatCurrency(investment.profit)}
                                  </p>
                                </div>
                                <Button
                                  variant="outline"
                                  size="icon"
                                  className="h-8 w-8 shrink-0"
                                  onClick={() => handleOpenAnalysis(investment.symbol, investment.buy_date)}
                                  title={`View ${investment.symbol} analysis`}
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Investments Table */}
              <div className="rounded-lg border bg-card p-6">
                <h2 className="mb-4 text-2xl font-semibold">
                  Investments ({allBacktestInvestments.length})
                </h2>
                <Tabs value={tableView} onValueChange={(v) => setTableView(v as "investment" | "rebalance")}>
                  <TabsList>
                    <TabsTrigger value="investment">By BacktestInvestment</TabsTrigger>
                    <TabsTrigger value="rebalance">By Rebalance</TabsTrigger>
                  </TabsList>

                  <TabsContent value="investment">
                    <BacktestInvestmentTable
                      investments={allBacktestInvestments}
                      formatDate={dateFormat}
                      formatCurrency={formatCurrency}
                      formatPercent={formatPercent}
                    />
                  </TabsContent>

                  <TabsContent value="rebalance">
                    <BacktestRebalanceTable
                      rebalanceHistory={backtestData.backtest_rebalance}
                      formatDate={dateFormat}
                      formatCurrency={formatCurrency}
                      formatPercent={formatPercent}
                    />
                  </TabsContent>
                </Tabs>
              </div>
            </>
          ) : null}
        </main>

      </div>

      {/* Analysis Panel */}
      {analysisPanelDate && (
        <AnalysisPanel
          symbol={analysisPanelSymbol || undefined}
          analysisDate={analysisPanelDate}
          backtestRule={backtestRule}
          involvedKeys={involvedKeys}
          onClose={handleCloseAnalysis}
        />
      )}
    </div>
  )
}
