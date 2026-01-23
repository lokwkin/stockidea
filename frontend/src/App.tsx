import { Routes, Route, Link, useLocation, Navigate, useParams } from "react-router-dom"
import { useState, useEffect } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { AnalysisView } from "@/components/AnalysisView"
import { SimulationView } from "@/components/SimulationView"
import { CreateSimulationView } from "@/components/CreateSimulationView"
import { cn } from "@/lib/utils"

function Sidebar() {
  const location = useLocation()
  const { file } = useParams<{ file?: string }>()
  const [simulations, setSimulations] = useState<string[]>([])
  const [isSimulationExpanded, setIsSimulationExpanded] = useState(false)
  const [loadingSimulations, setLoadingSimulations] = useState(true)

  const isSimulationPath = location.pathname.startsWith("/simulation")
  const isCreatePath = location.pathname === "/simulation/create"

  // Load simulations list
  useEffect(() => {
    fetch("/api/simulations")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load simulations list")
        return res.json()
      })
      .then((files: string[]) => {
        setSimulations(files)
        setLoadingSimulations(false)
      })
      .catch((err) => {
        console.error("Failed to load simulations:", err)
        setLoadingSimulations(false)
      })
  }, [])

  // Auto-expand simulation menu if we're on a simulation page
  useEffect(() => {
    if (isSimulationPath && !isCreatePath) {
      setIsSimulationExpanded(true)
    }
  }, [isSimulationPath, isCreatePath])

  return (
    <aside className="w-64 border-r bg-card/50 flex-shrink-0 flex flex-col">
      <div className="p-6 border-b">
        <h1 className="bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-2xl font-bold tracking-tight text-transparent">
          StockPick
        </h1>
      </div>
      <nav className="flex-1 p-2 overflow-y-auto">
        {/* Simulation Section */}
        <div className="mt-1">
          <button
            onClick={() => setIsSimulationExpanded(!isSimulationExpanded)}
            className={cn(
              "flex w-full items-center justify-between px-3 py-2 rounded-md text-base font-medium transition-all",
              isSimulationPath && !isCreatePath
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
          >
            <span>Simulation</span>
            {isSimulationExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
          {isSimulationExpanded && (
            <div className="ml-4 mt-1 space-y-1">
              <Link
                to="/simulation/create"
                className={cn(
                  "block w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-all",
                  isCreatePath
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                Create Simulation
              </Link>
              {loadingSimulations ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">Loading...</div>
              ) : simulations.length === 0 ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">No simulations</div>
              ) : (
                simulations.map((sim) => (
                  <Link
                    key={sim}
                    to={`/simulation/${sim}`}
                    className={cn(
                      "block w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-all truncate",
                      file === sim
                        ? "bg-muted text-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                    )}
                    title={sim}
                  >
                    {sim}
                  </Link>
                ))
              )}
            </div>
          )}
        </div>

        {/* Trend Data Section */}
        <Link
          to="/analysis"
          className={cn(
            "block w-full text-left px-3 py-2 rounded-md text-base font-medium transition-all mt-1",
            location.pathname.startsWith("/analysis")
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
        >
          Trend Data
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
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/analysis" replace />} />
            <Route path="/analysis" element={<AnalysisView />} />
            <Route path="/analysis/:file" element={<AnalysisView />} />
            <Route path="/simulation" element={<SimulationView />} />
            <Route path="/simulation/create" element={<CreateSimulationView />} />
            <Route path="/simulation/:file" element={<SimulationView />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
