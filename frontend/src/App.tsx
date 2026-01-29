import { Routes, Route, Link, useLocation, Navigate } from "react-router-dom"
import { useState, useEffect } from "react"
import { ChevronDown, ChevronRight, Plus, FolderTree, TrendingUp } from "lucide-react"
import { AnalysisView } from "@/components/AnalysisView"
import { SimulationView } from "@/components/SimulationView"
import { CreateSimulationView } from "@/components/CreateSimulationView"
import { SimulationSummary } from "@/types/simulation"
import { cn, dateFormat } from "@/lib/utils"

function Sidebar() {
  const location = useLocation()
  const [simulations, setSimulations] = useState<SimulationSummary[]>([])
  const [manuallyExpanded, setManuallyExpanded] = useState(false)
  const [loadingSimulations, setLoadingSimulations] = useState(true)
  const [isHovered, setIsHovered] = useState(false)

  const isSimulationPath = location.pathname.startsWith("/simulation") && location.pathname !== "/simulation/create"
  const isCreatePath = location.pathname === "/simulation/create"
  
  // Extract simulation ID from pathname (e.g., "/simulation/123" -> "123")
  const currentSimulationId = isSimulationPath
    ? location.pathname.replace("/simulation/", "").split("/")[0] || null
    : null

  // Compute expanded state: expand if on simulation path or manually expanded
  const isSimulationExpanded = isSimulationPath || manuallyExpanded

  // Load simulations list
  useEffect(() => {
    fetch("/api/simulations")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load simulations list")
        return res.json()
      })
      .then((sims: SimulationSummary[]) => {
        setSimulations(sims)
        setLoadingSimulations(false)
      })
      .catch((err) => {
        console.error("Failed to load simulations:", err)
        setLoadingSimulations(false)
      })
  }, [])

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
        {/* Create Simulation Section */}
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
          {isHovered ? (
            "Create Simulations"
          ) : (
            <Plus className="h-5 w-5" />
          )}
        </Link>

        {/* Simulation Section */}
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
                <span>Simulation</span>
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
          {isHovered ? (
            "Trend Data"
          ) : (
            <TrendingUp className="h-5 w-5" />
          )}
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
            <Route path="/simulation/:id" element={<SimulationView />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
