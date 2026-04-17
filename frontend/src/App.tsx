import { Routes, Route, Link, useLocation, Navigate } from "react-router-dom"
import { useState, useEffect, useRef, useCallback } from "react"
import { ChevronDown, ChevronRight, Plus, FolderTree, TrendingUp, BarChart3, Bot, User } from "lucide-react"
import dayjs from "dayjs"
import { AnalysisView } from "@/components/AnalysisView"
import { BacktestView } from "@/components/BacktestView"
import { CreateBacktestView } from "@/components/CreateBacktestView"
import { CreateStrategyView } from "@/components/CreateStrategyView"
import { StrategyView } from "@/components/StrategyView"
import { StockChartView } from "@/components/StockChartView"
import { BacktestSummary } from "@/types/backtest"
import { StrategySummary } from "@/types/strategy"
import { cn, dateFormat } from "@/lib/utils"

const STRATEGY_STATUS_COLORS: Record<string, string> = {
  idle: "bg-positive",
  running: "bg-info",
  failed: "bg-negative",
}

function StatusDot({ color, animate }: { color: string; animate?: boolean }) {
  return (
    <span className="relative inline-flex h-2 w-2 flex-shrink-0">
      {animate && (
        <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-75", color)} />
      )}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", color)} />
    </span>
  )
}

function formatMonthYear(dateStr: string): string {
  const d = dayjs(dateStr)
  return d.isValid() ? d.format("MMMYY") : ""
}

function Sidebar() {
  const location = useLocation()
  const [strategies, setStrategies] = useState<StrategySummary[]>([])
  const [backtests, setBacktests] = useState<BacktestSummary[]>([])
  const [strategiesExpanded, setStrategiesExpanded] = useState(true)
  const [backtestsExpanded, setBacktestsExpanded] = useState(true)
  const [loadingBacktests, setLoadingBacktests] = useState(true)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const isBacktestPath = location.pathname.startsWith("/backtest") && location.pathname !== "/backtest/create"
  const isCreatePath = location.pathname === "/backtest/create"
  const isStrategyPath = location.pathname.startsWith("/strategy")
  const isCreateStrategyPath = location.pathname === "/strategy/create"

  const currentBacktestId = isBacktestPath
    ? location.pathname.replace("/backtest/", "").split("/")[0] || null
    : null

  const currentStrategyId = isStrategyPath && !isCreateStrategyPath
    ? location.pathname.replace("/strategy/", "").split("/")[0] || null
    : null

  const fetchStrategies = useCallback(() => {
    fetch("/api/strategies")
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then((data: StrategySummary[]) => setStrategies(data))
      .catch(() => {})
  }, [])

  const fetchBacktests = useCallback(() => {
    fetch("/api/backtests")
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then((sims: BacktestSummary[]) => {
        setBacktests(sims)
        setLoadingBacktests(false)
      })
      .catch(() => setLoadingBacktests(false))
  }, [])

  const strategiesRef = useRef<StrategySummary[]>(strategies)
  useEffect(() => { strategiesRef.current = strategies }, [strategies])

  const refreshStrategies = useCallback(() => {
    fetch("/api/strategies")
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then((data: StrategySummary[]) => {
        const hadRunning = strategiesRef.current.some((s) => s.status === "running")
        const nowRunning = data.some((s) => s.status === "running")
        setStrategies(data)
        // Refresh backtests when a running strategy finishes (it may have created new ones).
        if (hadRunning && !nowRunning) fetchBacktests()
      })
      .catch(() => {})
  }, [fetchBacktests])

  // Initial load
  useEffect(() => {
    fetchStrategies()
    fetchBacktests()
  }, [])

  // Adaptive polling for strategies (faster while one is running).
  useEffect(() => {
    const hasRunningStrategy = strategies.some((s) => s.status === "running")
    const interval = hasRunningStrategy ? 3000 : 15000
    pollRef.current = setTimeout(() => {
      refreshStrategies()
    }, interval)
    return () => { if (pollRef.current) clearTimeout(pollRef.current) }
  }, [strategies, refreshStrategies])

  const strategyNameById = new Map<string, string>()
  for (const s of strategies) strategyNameById.set(String(s.id), s.name)

  const renderBacktestLink = (sim: BacktestSummary) => {
    const profit = sim.profit_pct
    const profitStr = `${profit >= 0 ? "+" : ""}${profit.toFixed(2)}%`
    const period = `${formatMonthYear(sim.date_start)} → ${formatMonthYear(sim.date_end)}`
    const indexLabel = sim.index === "NASDAQ" ? "NASDAQ" : sim.index === "SP500" ? "S&P500" : sim.index
    const isAi = !!sim.strategy_id
    const owner = isAi ? strategyNameById.get(String(sim.strategy_id)) ?? "AI Strategy" : "User Triggered"
    const fullTitle = `${dateFormat(sim.date_start)} - ${dateFormat(sim.date_end)} (${indexLabel}) — ${owner}`
    return (
      <Link
        key={sim.id}
        to={`/backtest/${sim.id}`}
        className={cn(
          "flex items-center gap-2 w-full px-3 py-1 rounded-md text-xs transition-colors",
          currentBacktestId === String(sim.id)
            ? "bg-accent text-foreground font-medium border-l-2 border-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-accent"
        )}
        title={fullTitle}
      >
        <span className="flex-shrink-0 text-muted-foreground" title={owner}>
          {isAi ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
        </span>
        <span
          className={cn(
            "font-mono tabular-nums flex-shrink-0",
            profit > 0 ? "text-positive" : profit < 0 ? "text-negative" : ""
          )}
        >
          [{profitStr}]
        </span>
        <span className="font-mono tabular-nums flex-shrink-0 text-muted-foreground">{period}</span>
        <span className="flex-shrink-0 text-muted-foreground">({indexLabel})</span>
      </Link>
    )
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-[360px] border-r bg-sidebar flex-shrink-0 flex flex-col z-50">
      <div className="border-b px-5 py-5">
        <h1 className="text-base font-semibold text-foreground tracking-tight">
          StockIdea
        </h1>
      </div>
      <nav className="flex-1 px-3 py-3 overflow-y-auto text-sm">
        {/* Strategies Section */}
        <div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setStrategiesExpanded(!strategiesExpanded)}
              className={cn(
                "flex flex-1 items-center justify-between px-3 py-1.5 rounded-md font-medium transition-colors",
                isStrategyPath && !isCreateStrategyPath
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <span className="flex items-center gap-2">
                <Bot className="h-4 w-4" />
                Strategies
                {strategies.length > 0 && (
                  <span className="text-xs text-muted-foreground/60">{strategies.length}</span>
                )}
              </span>
              {strategiesExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            </button>
            <Link
              to="/strategy/create"
              className={cn(
                "flex items-center justify-center h-7 w-7 rounded-md transition-colors",
                isCreateStrategyPath
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
              title="New Strategy"
            >
              <Plus className="h-4 w-4" />
            </Link>
          </div>

          {strategiesExpanded && (
            <div className="ml-4 mt-0.5 space-y-1">
              {strategies.length === 0 ? (
                <div className="px-3 py-1.5 text-xs text-muted-foreground">No strategies yet</div>
              ) : (
                strategies.map((s) => (
                  <Link
                    key={s.id}
                    to={`/strategy/${s.id}`}
                    className={cn(
                      "flex items-center gap-2 w-full rounded-md py-1.5 px-3 transition-colors",
                      currentStrategyId === s.id
                        ? "bg-accent text-foreground font-medium border-l-2 border-primary"
                        : "text-muted-foreground hover:text-foreground hover:bg-accent"
                    )}
                    title={s.instruction}
                  >
                    <StatusDot
                      color={STRATEGY_STATUS_COLORS[s.status] || "bg-gray-400"}
                      animate={s.status === "running"}
                    />
                    <span className="truncate flex-1 text-sm">{s.name}</span>
                  </Link>
                ))
              )}
            </div>
          )}
        </div>

        {/* Backtests Section (flat list of all) */}
        <div className="mt-3 pt-3 border-t border-sidebar-border">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setBacktestsExpanded(!backtestsExpanded)}
              className={cn(
                "flex flex-1 items-center justify-between px-3 py-1.5 rounded-md font-medium transition-colors",
                isBacktestPath
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <span className="flex items-center gap-2">
                <FolderTree className="h-4 w-4" />
                Backtests
                {backtests.length > 0 && (
                  <span className="text-xs text-muted-foreground/60">{backtests.length}</span>
                )}
              </span>
              {backtestsExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            </button>
            <Link
              to="/backtest/create"
              className={cn(
                "flex items-center justify-center h-7 w-7 rounded-md transition-colors",
                isCreatePath
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
              title="New Backtest"
            >
              <Plus className="h-4 w-4" />
            </Link>
          </div>
          {backtestsExpanded && (
            <div className="ml-4 mt-0.5 space-y-0.5">
              {loadingBacktests ? (
                <div className="px-3 py-1 text-xs text-muted-foreground">Loading...</div>
              ) : backtests.length === 0 ? (
                <div className="px-3 py-1 text-xs text-muted-foreground">No backtests</div>
              ) : (
                [...backtests]
                  .sort((a, b) => dayjs(b.created_at).valueOf() - dayjs(a.created_at).valueOf())
                  .map(renderBacktestLink)
              )}
            </div>
          )}
        </div>

        {/* Indicators Section */}
        <div className="mt-3 pt-3 border-t border-sidebar-border">
          <Link
            to="/analysis"
            className={cn(
              "flex items-center w-full text-left px-3 py-1.5 rounded-md font-medium transition-colors",
              location.pathname.startsWith("/analysis")
                ? "bg-accent text-foreground border-l-2 border-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            )}
          >
            <TrendingUp className="h-4 w-4 mr-2" />
            Indicators
          </Link>
        </div>

        {/* Stocks Section */}
        <div className="mt-3 pt-3 border-t border-sidebar-border">
          <Link
            to="/chart"
            className={cn(
              "flex items-center w-full text-left px-3 py-1.5 rounded-md font-medium transition-colors",
              location.pathname.startsWith("/chart")
                ? "bg-accent text-foreground border-l-2 border-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            )}
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            Stocks
          </Link>
        </div>
      </nav>
    </aside>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-background">
      <div className="flex h-screen">
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto ml-[360px]">
          <Routes>
            <Route path="/" element={<Navigate to="/strategy/create" replace />} />
            <Route path="/strategy/create" element={<CreateStrategyView />} />
            <Route path="/strategy/:id" element={<StrategyView />} />
            <Route path="/analysis" element={<AnalysisView />} />
            <Route path="/analysis/:date" element={<AnalysisView />} />
            <Route path="/chart" element={<StockChartView />} />
            <Route path="/chart/:symbol" element={<StockChartView />} />
            <Route path="/backtest" element={<BacktestView />} />
            <Route path="/backtest/create" element={<CreateBacktestView />} />
            <Route path="/backtest/:id" element={<BacktestView />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
