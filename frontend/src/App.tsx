import { useState } from "react"
import { AnalysisView } from "@/components/AnalysisView"
import { SimulationView } from "@/components/SimulationView"
import { cn } from "@/lib/utils"

function App() {
  const [activeTab, setActiveTab] = useState("analysis")
  const [analysisFile, setAnalysisFile] = useState<string | null>(null)

  const handleNavigateToAnalysis = (file: string) => {
    setAnalysisFile(file)
    setActiveTab("analysis")
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent" />

      <div className="flex h-screen">
        {/* Left Sidebar */}
        <aside className="w-64 border-r bg-card/50 flex-shrink-0 flex flex-col">
          <div className="p-6 border-b">
            <h1 className="bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-2xl font-bold tracking-tight text-transparent">
              StockPick
            </h1>
          </div>
          <nav className="flex-1 p-2">
            <button
              type="button"
              onClick={() => {
                setActiveTab("simulation")
                setAnalysisFile(null)
              }}
              className={cn(
                "w-full text-left px-3 py-2 rounded-md text-base font-medium transition-all mt-1",
                activeTab === "simulation"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              Simulation
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab("analysis")
                setAnalysisFile(null)
              }}
              className={cn(
                "w-full text-left px-3 py-2 rounded-md text-base font-medium transition-all",
                activeTab === "analysis"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              Analysis
            </button>
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto">
          {activeTab === "analysis" && (
            <AnalysisView initialFile={analysisFile} onFileSelected={() => setAnalysisFile(null)} />
          )}
          {activeTab === "simulation" && (
            <SimulationView onNavigateToAnalysis={handleNavigateToAnalysis} />
          )}
        </main>
      </div>
    </div>
  )
}

export default App
