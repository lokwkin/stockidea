import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type StockIndex = "SP500" | "DOWJONES" | "NASDAQ"

interface SimulateRequest {
  max_stocks: number
  rebalance_interval_weeks: number
  date_start: string // ISO datetime string
  date_end: string // ISO datetime string
  rule: string
  index: StockIndex
}

export function CreateSimulationView() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState<SimulateRequest>({
    max_stocks: 10,
    rebalance_interval_weeks: 4,
    date_start: "",
    date_end: "",
    rule: "",
    index: "SP500",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Convert date strings to ISO datetime strings
      const dateStart = new Date(formData.date_start + "T00:00:00").toISOString()
      const dateEnd = new Date(formData.date_end + "T23:59:59").toISOString()

      const response = await fetch("/api/simulate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...formData,
          date_start: dateStart,
          date_end: dateEnd,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to create simulation" }))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      await response.json()

      // Fetch the list of simulations to get the newly created one
      // The simulation is saved with filename: simulation_YYYYMMDD_HHMMSS.json
      const simulationsResponse = await fetch("/api/simulations")
      if (simulationsResponse.ok) {
        const simulations = await simulationsResponse.json()
        if (simulations.length > 0) {
          // Navigate to the most recent simulation (should be the one we just created)
          setLoading(false)
          navigate(`/simulation/${simulations[0]}`)
          return
        }
      }

      // Fallback: navigate to simulation list
      setLoading(false)
      navigate("/simulation")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create simulation")
      setLoading(false)
    }
  }

  const handleChange = (field: keyof SimulateRequest, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  // Set default dates on mount
  useEffect(() => {
    const getDefaultStartDate = () => {
      const date = new Date()
      date.setFullYear(date.getFullYear() - 1)
      return date.toISOString().split("T")[0]
    }

    const getDefaultEndDate = () => {
      return new Date().toISOString().split("T")[0]
    }

    setFormData((prev) => ({
      ...prev,
      date_start: prev.date_start || getDefaultStartDate(),
      date_end: prev.date_end || getDefaultEndDate(),
    }))
  }, [])

  return (
    <div className="relative mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8">
        <h1 className="mb-2 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
          Create Simulation
        </h1>
        <p className="text-muted-foreground">
          Configure and run a new investment strategy simulation
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm font-medium text-destructive">{error}</p>
          </div>
        )}

        <div className="rounded-lg border bg-card p-6 space-y-6">
          {/* Stock Index Selection */}
          <div className="space-y-2">
            <label htmlFor="index" className="text-sm font-medium">
              Stock Index
            </label>
            <Select
              value={formData.index}
              onValueChange={(value) => handleChange("index", value as StockIndex)}
            >
              <SelectTrigger id="index">
                <SelectValue placeholder="Select an index" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SP500">S&P 500</SelectItem>
                <SelectItem value="DOWJONES">Dow Jones</SelectItem>
                <SelectItem value="NASDAQ">NASDAQ</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              The stock index to use as the universe for stock selection
            </p>
          </div>

          {/* Max Stocks */}
          <div className="space-y-2">
            <label htmlFor="max_stocks" className="text-sm font-medium">
              Maximum Stocks
            </label>
            <Input
              id="max_stocks"
              type="number"
              min="1"
              max="100"
              value={formData.max_stocks}
              onChange={(e) => handleChange("max_stocks", parseInt(e.target.value) || 0)}
              required
            />
            <p className="text-xs text-muted-foreground">
              Maximum number of stocks to hold in the portfolio
            </p>
          </div>

          {/* Rebalance Interval */}
          <div className="space-y-2">
            <label htmlFor="rebalance_interval_weeks" className="text-sm font-medium">
              Rebalance Interval (weeks)
            </label>
            <Input
              id="rebalance_interval_weeks"
              type="number"
              min="1"
              max="52"
              value={formData.rebalance_interval_weeks}
              onChange={(e) => handleChange("rebalance_interval_weeks", parseInt(e.target.value) || 0)}
              required
            />
            <p className="text-xs text-muted-foreground">
              How often to rebalance the portfolio (in weeks)
            </p>
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="date_start" className="text-sm font-medium">
                Start Date
              </label>
              <Input
                id="date_start"
                type="date"
                value={formData.date_start}
                onChange={(e) => handleChange("date_start", e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">Simulation start date</p>
            </div>

            <div className="space-y-2">
              <label htmlFor="date_end" className="text-sm font-medium">
                End Date
              </label>
              <Input
                id="date_end"
                type="date"
                value={formData.date_end}
                onChange={(e) => handleChange("date_end", e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">Simulation end date</p>
            </div>
          </div>

          {/* Rule */}
          <div className="space-y-2">
            <label htmlFor="rule" className="text-sm font-medium">
              Selection Rule
            </label>
            <textarea
              id="rule"
              value={formData.rule}
              onChange={(e) => handleChange("rule", e.target.value)}
              required
              rows={8}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none font-mono"
              placeholder="Enter your stock selection rule (Python expression)..."
            />
            <p className="text-xs text-muted-foreground">
              Python expression that evaluates to True/False for stock selection. Use variables like{" "}
              <code className="rounded bg-muted px-1 py-0.5 text-xs">annualized_slope</code>,{" "}
              <code className="rounded bg-muted px-1 py-0.5 text-xs">trend_r_squared</code>,{" "}
              <code className="rounded bg-muted px-1 py-0.5 text-xs">change_1y_pct</code>, etc.
            </p>
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex items-center justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/simulation")}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Creating...
              </>
            ) : (
              "Create Simulation"
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
