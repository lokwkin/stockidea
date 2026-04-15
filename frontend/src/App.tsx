import { Routes, Route, Link, useLocation, Navigate } from "react-router-dom"
import { useState, useEffect, useRef, useCallback } from "react"
import { ChevronDown, ChevronRight, Plus, FolderTree, TrendingUp, Loader2, Bot } from "lucide-react"
import { AnalysisView } from "@/components/AnalysisView"
import { BacktestView } from "@/components/BacktestView"
import { CreateBacktestView } from "@/components/CreateBacktestView"
import { BacktestJobView } from "@/components/BacktestJobView"
import { CreateStrategyView } from "@/components/CreateStrategyView"
import { StrategyView } from "@/components/StrategyView"
import { BacktestJob, BacktestSummary } from "@/types/backtest"
import { StrategySummary } from "@/types/strategy"
import { cn, dateFormat } from "@/lib/utils"

const JOB_STATUS_COLORS: Record<BacktestJob["status"], string> = {
  pending: "bg-yellow-400",
  running: "bg-blue-400",
  completed: "bg-green-400",
  failed: "bg-red-400",
}

const STRATEGY_STATUS_COLORS: Record<string, string> = {
  idle: "bg-green-400",
  running: "bg-blue-400",
  failed: "bg-red-400",
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

function Sidebar() {
  const location = useLocation()
  const [strategies, setStrategies] = useState<StrategySummary[]>([])
  const [backtests, setBacktests] = useState<BacktestSummary[]>([])
  const [jobs, setJobs] = useState<BacktestJob[]>([])
  const [strategiesExpanded, setStrategiesExpanded] = useState(true)
  const [backtestsExpanded, setBacktestsExpanded] = useState(false)
  const [jobsExpanded, setJobsExpanded] = useState(false)
  const [loadingBacktests, setLoadingBacktests] = useState(true)
  const [isHovered, setIsHovered] = useState(false)
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

  const jobsRef = useRef<BacktestJob[]>(jobs)
  useEffect(() => { jobsRef.current = jobs }, [jobs])

  const fetchJobs = useCallback(() => {
    fetch("/api/jobs")
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then((data: BacktestJob[]) => {
        const hadActive = jobsRef.current.some((j) => j.status === "pending" || j.status === "running")
        const nowActive = data.some((j) => j.status === "pending" || j.status === "running")
        setJobs(data)
        if (hadActive && !nowActive) fetchBacktests()
      })
      .catch(() => {})
  }, [fetchBacktests])

  // Initial load
  useEffect(() => {
    fetchStrategies()
    fetchBacktests()
    fetchJobs()
  }, [])

  // Adaptive polling
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === "pending" || j.status === "running")
    const hasRunningStrategy = strategies.some((s) => s.status === "running")
    const interval = (hasActive || hasRunningStrategy) ? 3000 : 15000
    pollRef.current = setTimeout(() => {
      fetchJobs()
      fetchStrategies()
    }, interval)
    return () => { if (pollRef.current) clearTimeout(pollRef.current) }
  }, [jobs, strategies])

  const activeJobs = jobs.filter((j) => j.status === "pending" || j.status === "running")
  const recentJobs = jobs.slice(0, 8)
  const hasActiveJobs = activeJobs.length > 0

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-screen border-r flex-shrink-0 flex flex-col transition-all duration-300 ease-in-out z-50",
        isHovered ? "w-80 bg-card shadow-xl" : "w-16 bg-card/50 shadow-lg"
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className={cn("border-b transition-all duration-300", isHovered ? "p-6" : "p-4")}>
        <h1 className={cn(
          "bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text font-bold tracking-tight text-transparent transition-all duration-300",
          isHovered ? "text-2xl" : "text-lg truncate"
        )}>
          {isHovered ? "StockPick" : "SP"}
        </h1>
      </div>
      <nav className="flex-1 p-2 overflow-y-auto">
        {/* New Strategy */}
        <Link
          to="/strategy/create"
          className={cn(
            "flex items-center w-full text-left px-3 py-2 rounded-md font-medium transition-all mt-1",
            isHovered ? "text-base" : "text-sm justify-center",
            isCreateStrategyPath
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title={!isHovered ? "New Strategy" : undefined}
        >
          {isHovered ? (
            <>
              <Plus className="h-4 w-4 mr-2" />
              New Strategy
            </>
          ) : (
            <Plus className="h-5 w-5" />
          )}
        </Link>

        {/* Strategies Section */}
        <div className="mt-1">
          <button
            onClick={() => setStrategiesExpanded(!strategiesExpanded)}
            className={cn(
              "flex w-full items-center px-3 py-2 rounded-md font-medium transition-all",
              isHovered ? "text-base justify-between" : "text-sm justify-center",
              isStrategyPath && !isCreateStrategyPath
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
            title={!isHovered ? "Strategies" : undefined}
          >
            {isHovered ? (
              <>
                <span className="flex items-center gap-2">
                  <Bot className="h-4 w-4" />
                  Strategies
                </span>
                {strategiesExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </>
            ) : (
              <Bot className="h-5 w-5" />
            )}
          </button>

          {strategiesExpanded && isHovered && (
            <div className="ml-4 mt-1 space-y-1">
              {strategies.length === 0 ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">No strategies yet</div>
              ) : (
                strategies.map((s) => (
                  <Link
                    key={s.id}
                    to={`/strategy/${s.id}`}
                    className={cn(
                      "flex items-center gap-2 w-full px-3 py-2 rounded-md text-sm font-medium transition-all",
                      currentStrategyId === s.id
                        ? "bg-muted text-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                    )}
                    title={s.instruction}
                  >
                    <StatusDot
                      color={STRATEGY_STATUS_COLORS[s.status] || "bg-gray-400"}
                      animate={s.status === "running"}
                    />
                    <span className="truncate flex-1">{s.name}</span>
                  </Link>
                ))
              )}
            </div>
          )}
        </div>

        {/* Jobs Section */}
        <div className="mt-1">
          <button
            onClick={() => setJobsExpanded(!jobsExpanded)}
            className={cn(
              "flex w-full items-center px-3 py-2 rounded-md font-medium transition-all",
              isHovered ? "text-base justify-between" : "text-sm justify-center",
              "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
            title={!isHovered ? "Jobs" : undefined}
          >
            {isHovered ? (
              <>
                <span className="flex items-center gap-2">
                  Jobs
                  {hasActiveJobs && (
                    <span className="flex items-center gap-1 rounded-full bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {activeJobs.length}
                    </span>
                  )}
                </span>
                {jobsExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </>
            ) : (
              <span className="relative">
                <Loader2 className={cn("h-5 w-5", hasActiveJobs && "animate-spin text-blue-400")} />
                {hasActiveJobs && (
                  <span className="absolute -right-1 -top-1 flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-400" />
                  </span>
                )}
              </span>
            )}
          </button>

          {jobsExpanded && isHovered && (
            <div className="ml-4 mt-1 space-y-1">
              {recentJobs.length === 0 ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">No jobs yet</div>
              ) : (
                recentJobs.map((job) => {
                  const isActive = job.status === "pending" || job.status === "running"
                  const href = job.status === "completed" && job.backtest_id
                    ? `/backtest/${job.backtest_id}`
                    : `/backtest/job/${job.id}`
                  const label = job.status === "completed" && job.backtest_id
                    ? "View result"
                    : job.status === "failed"
                    ? "Failed"
                    : job.status === "running"
                    ? "Running..."
                    : "Queued"
                  return (
                    <Link
                      key={job.id}
                      to={href}
                      className={cn(
                        "flex items-center gap-2 w-full px-3 py-2 rounded-md text-sm font-medium transition-all",
                        "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                      )}
                      title={`Job ${job.id}`}
                    >
                      <StatusDot color={JOB_STATUS_COLORS[job.status]} animate={isActive} />
                      <span className="truncate flex-1">{label}</span>
                      <span className="text-xs text-muted-foreground/60 flex-shrink-0">
                        {new Date(job.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </Link>
                  )
                })
              )}
            </div>
          )}
        </div>

        {/* Create Backtest */}
        <Link
          to="/backtest/create"
          className={cn(
            "flex items-center w-full text-left px-3 py-2 rounded-md font-medium transition-all mt-1",
            isHovered ? "text-base" : "text-sm justify-center",
            isCreatePath
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title={!isHovered ? "Create Backtest" : undefined}
        >
          {isHovered ? "Create Backtest" : <Plus className="h-5 w-5" />}
        </Link>

        {/* Backtest Results Section */}
        <div className="mt-1">
          <button
            onClick={() => setBacktestsExpanded(!backtestsExpanded)}
            className={cn(
              "flex w-full items-center justify-between px-3 py-2 rounded-md font-medium transition-all",
              isHovered ? "text-base" : "text-sm justify-center",
              isBacktestPath
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
            title={!isHovered ? "Backtests" : undefined}
          >
            {isHovered ? (
              <>
                <span>Backtests</span>
                {backtestsExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </>
            ) : (
              <FolderTree className="h-5 w-5" />
            )}
          </button>
          {backtestsExpanded && isHovered && (
            <div className="ml-4 mt-1 space-y-1">
              {loadingBacktests ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">Loading...</div>
              ) : backtests.length === 0 ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">No backtests</div>
              ) : (
                backtests.map((sim) => {
                  const dateStart = dateFormat(sim.date_start)
                  const dateEnd = dateFormat(sim.date_end)
                  const displayName = `${dateStart} - ${dateEnd} (${sim.profit_pct.toFixed(1)}%)`
                  return (
                    <Link
                      key={sim.id}
                      to={`/backtest/${sim.id}`}
                      className={cn(
                        "block w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-all truncate",
                        currentBacktestId === String(sim.id)
                          ? "bg-muted text-foreground"
                          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                      )}
                      title={displayName}
                    >
                      {displayName}
                    </Link>
                  )
                })
              )}
            </div>
          )}
        </div>

        {/* Trend Data Section */}
        <Link
          to="/analysis"
          className={cn(
            "flex items-center w-full text-left px-3 py-2 rounded-md font-medium transition-all mt-1",
            isHovered ? "text-base" : "text-sm justify-center",
            location.pathname.startsWith("/analysis")
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title={!isHovered ? "Trend Data" : undefined}
        >
          {isHovered ? "Trend Data" : <TrendingUp className="h-5 w-5" />}
        </Link>
      </nav>
    </aside>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-background">
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent" />

      <div className="flex h-screen">
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto ml-16">
          <Routes>
            <Route path="/" element={<Navigate to="/strategy/create" replace />} />
            <Route path="/strategy/create" element={<CreateStrategyView />} />
            <Route path="/strategy/:id" element={<StrategyView />} />
            <Route path="/analysis" element={<AnalysisView />} />
            <Route path="/analysis/:date" element={<AnalysisView />} />
            <Route path="/backtest" element={<BacktestView />} />
            <Route path="/backtest/create" element={<CreateBacktestView />} />
            <Route path="/backtest/job/:jobId" element={<BacktestJobView />} />
            <Route path="/backtest/:id" element={<BacktestView />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
