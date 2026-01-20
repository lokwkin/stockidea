import { Routes, Route, Link, useLocation, Navigate } from "react-router-dom"
import { AnalysisView } from "@/components/AnalysisView"
import { SimulationView } from "@/components/SimulationView"
import { cn } from "@/lib/utils"

function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-64 border-r bg-card/50 flex-shrink-0 flex flex-col">
      <div className="p-6 border-b">
        <h1 className="bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-2xl font-bold tracking-tight text-transparent">
          StockPick
        </h1>
      </div>
      <nav className="flex-1 p-2">
        <Link
          to="/simulation"
          className={cn(
            "block w-full text-left px-3 py-2 rounded-md text-base font-medium transition-all mt-1",
            location.pathname.startsWith("/simulation")
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
        >
          Simulation
        </Link>
        <Link
          to="/analysis"
          className={cn(
            "block w-full text-left px-3 py-2 rounded-md text-base font-medium transition-all",
            location.pathname.startsWith("/analysis")
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
        >
          Analysis
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
            <Route path="/simulation/:file" element={<SimulationView />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
