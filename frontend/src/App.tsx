import { Routes, Route, Link, useLocation, Navigate } from "react-router-dom"
import { useState, useEffect, useRef, useCallback } from "react"
import { ChevronDown, ChevronRight, Plus, FolderTree, TrendingUp, Loader2, Bot } from "lucide-react"
import { AnalysisView } from "@/components/AnalysisView"
import { SimulationView } from "@/components/SimulationView"
import { CreateSimulationView } from "@/components/CreateSimulationView"
import { SimulationJobView } from "@/components/SimulationJobView"
import { AgentView } from "@/components/AgentView"
import { SimulationJob, SimulationSummary } from "@/types/simulation"
import { cn, dateFormat } from "@/lib/utils"

const JOB_STATUS_COLORS: Record<SimulationJob["status"], string> = {
  pending: "bg-yellow-400",
  running: "bg-blue-400",
  completed: "bg-green-400",
  failed: "bg-red-400",
}

function JobStatusDot({ status, animate }: { status: SimulationJob["status"]; animate?: boolean }) {
  return (
    <span className="relative inline-flex h-2 w-2 flex-shrink-0">
      {animate && (
        <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-75", JOB_STATUS_COLORS[status])} />
      )}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", JOB_STATUS_COLORS[status])} />
    </span>
  )
}

function Sidebar() {
  const location = useLocation()
  const [simulations, setSimulations] = useState<SimulationSummary[]>([])
  const [jobs, setJobs] = useState<SimulationJob[]>([])
  const [manuallyExpanded, setManuallyExpanded] = useState(false)
  const [jobsExpanded, setJobsExpanded] = useState(true)
  const [loadingSimulations, setLoadingSimulations] = useState(true)
  const [isHovered, setIsHovered] = useState(false)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const isSimulationPath = location.pathname.startsWith("/simulation") && location.pathname !== "/simulation/create"
  const isCreatePath = location.pathname === "/simulation/create"

  const currentSimulationId = isSimulationPath
    ? location.pathname.replace("/simulation/", "").split("/")[0] || null
    : null

  const isSimulationExpanded = isSimulationPath || manuallyExpanded

  const fetchSimulations = useCallback(() => {
    fetch("/api/simulations")
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then((sims: SimulationSummary[]) => {
        setSimulations(sims)
        setLoadingSimulations(false)
      })
      .catch(() => setLoadingSimulations(false))
  }, [])

  const jobsRef = useRef<SimulationJob[]>(jobs)
  useEffect(() => { jobsRef.current = jobs }, [jobs])

  const fetchJobs = useCallback(() => {
    fetch("/api/jobs")
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then((data: SimulationJob[]) => {
        const hadActive = jobsRef.current.some((j) => j.status === "pending" || j.status === "running")
        const nowActive = data.some((j) => j.status === "pending" || j.status === "running")
        setJobs(data)
        // Refresh simulations list when a job just completed
        if (hadActive && !nowActive) fetchSimulations()
      })
      .catch(() => {})
  }, [fetchSimulations])

  // Initial load
  useEffect(() => {
    fetchSimulations()
  }, [])

  // Adaptive polling: fast when jobs are active, slow otherwise
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === "pending" || j.status === "running")
    const interval = hasActive ? 3000 : 15000
    pollRef.current = setTimeout(fetchJobs, interval)
    return () => { if (pollRef.current) clearTimeout(pollRef.current) }
  }, [jobs])

  // Kick off first jobs fetch immediately
  useEffect(() => {
    fetchJobs()
  }, [])

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
        {/* Create Simulation */}
        <Link
          to="/simulation/create"
          className={cn(
            "flex items-center w-full text-left px-3 py-2 rounded-md font-medium transition-all mt-1",
            isHovered ? "text-base" : "text-sm justify-center",
            isCreatePath
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title={!isHovered ? "Create Simulations" : undefined}
        >
          {isHovered ? "Create Simulations" : <Plus className="h-5 w-5" />}
        </Link>

        {/* AI Agent */}
        <Link
          to="/agent"
          className={cn(
            "flex items-center w-full text-left px-3 py-2 rounded-md font-medium transition-all mt-1",
            isHovered ? "text-base" : "text-sm justify-center",
            location.pathname === "/agent"
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title={!isHovered ? "AI Agent" : undefined}
        >
          {isHovered ? "AI Agent" : <Bot className="h-5 w-5" />}
        </Link>

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
                  const href = job.status === "completed" && job.simulation_id
                    ? `/simulation/${job.simulation_id}`
                    : `/simulation/job/${job.id}`
                  const label = job.status === "completed" && job.simulation_id
                    ? "View result"
                    : job.status === "failed"
                    ? "Failed"
                    : job.status === "running"
                    ? "Running…"
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
                      <JobStatusDot status={job.status} animate={isActive} />
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

        {/* Simulation Results Section */}
        <div className="mt-1">
          <button
            onClick={() => setManuallyExpanded(!manuallyExpanded)}
            className={cn(
              "flex w-full items-center justify-between px-3 py-2 rounded-md font-medium transition-all",
              isHovered ? "text-base" : "text-sm justify-center",
              isSimulationPath
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
            title={!isHovered ? "Simulation" : undefined}
          >
            {isHovered ? (
              <>
                <span>Simulations</span>
                {isSimulationExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </>
            ) : (
              <FolderTree className="h-5 w-5" />
            )}
          </button>
          {isSimulationExpanded && isHovered && (
            <div className="ml-4 mt-1 space-y-1">
              {loadingSimulations ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">Loading...</div>
              ) : simulations.length === 0 ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">No simulations</div>
              ) : (
                simulations.map((sim) => {
                  const dateStart = dateFormat(sim.date_start)
                  const dateEnd = dateFormat(sim.date_end)
                  const displayName = `${dateStart} - ${dateEnd} (${(sim.profit_pct * 100).toFixed(1)}%)`
                  return (
                    <Link
                      key={sim.id}
                      to={`/simulation/${sim.id}`}
                      className={cn(
                        "block w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-all truncate",
                        currentSimulationId === String(sim.id)
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
            <Route path="/" element={<Navigate to="/analysis" replace />} />
            <Route path="/analysis" element={<AnalysisView />} />
            <Route path="/analysis/:date" element={<AnalysisView />} />
            <Route path="/simulation" element={<SimulationView />} />
            <Route path="/simulation/create" element={<CreateSimulationView />} />
            <Route path="/agent" element={<AgentView />} />
            <Route path="/simulation/job/:jobId" element={<SimulationJobView />} />
            <Route path="/simulation/:id" element={<SimulationView />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
