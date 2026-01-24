import { useState, useEffect, useRef } from "react"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

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
    max_stocks: 3,
    rebalance_interval_weeks: 2,
    date_start: "",
    date_end: "",
    rule: "",
    index: "SP500",
  })
  // Store string values for numeric inputs to allow empty state
  const [maxStocksInput, setMaxStocksInput] = useState<string>("3")
  const [rebalanceIntervalInput, setRebalanceIntervalInput] = useState<string>("2")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Format date from yyyy-mm-dd (ISO) to yyyy/mm/dd for display
  const formatDateForDisplay = (dateStr: string): string => {
    if (!dateStr) return ""
    return dateStr.replace(/-/g, "/")
  }
  
  // Convert yyyy/mm/dd input to yyyy-mm-dd (ISO) for storage
  const parseDateInput = (dateStr: string): string => {
    if (!dateStr) return ""
    return dateStr.split("/").join("-")
  }
  
  // Validate date format yyyy/mm/dd
  const isValidDate = (dateStr: string): boolean => {
    if (!dateStr) return false
    const datePattern = new RegExp("^\\d{4}/\\d{2}/\\d{2}$")
    if (!datePattern.test(dateStr)) return false
    const [year, month, day] = dateStr.split("/").map(Number)
    const date = new Date(year, month - 1, day)
    return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Convert input strings to numbers, using current formData values as fallback
      const maxStocks = maxStocksInput === "" ? formData.max_stocks : parseInt(maxStocksInput) || 0
      const rebalanceInterval = rebalanceIntervalInput === "" ? formData.rebalance_interval_weeks : parseInt(rebalanceIntervalInput) || 0

      // Validate numeric inputs
      if (maxStocks <= 0) {
        throw new Error("Maximum stocks must be greater than 0")
      }
      if (rebalanceInterval <= 0) {
        throw new Error("Rebalance interval must be greater than 0")
      }

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
          max_stocks: maxStocks,
          rebalance_interval_weeks: rebalanceInterval,
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
  
  const handleDateChange = (field: "date_start" | "date_end", value: string) => {
    // Convert yyyy/mm/dd to yyyy-mm-dd for storage
    const isoDate = parseDateInput(value)
    handleChange(field, isoDate)
  }
  
  const insertVariableAtCursor = (variable: string) => {
    const textarea = textareaRef.current
    if (!textarea) return
    
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = formData.rule
    const before = text.substring(0, start)
    const after = text.substring(end)
    
    const newText = before + variable + after
    handleChange("rule", newText)
    
    // Restore cursor position after the inserted variable
    setTimeout(() => {
      const newCursorPos = start + variable.length
      textarea.focus()
      textarea.setSelectionRange(newCursorPos, newCursorPos)
    }, 0)
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
              value={maxStocksInput}
              onChange={(e) => {
                const value = e.target.value
                setMaxStocksInput(value)
                // Update formData only if value is valid number
                const numValue = parseInt(value)
                if (!isNaN(numValue) && numValue > 0) {
                  handleChange("max_stocks", numValue)
                }
              }}
              onBlur={(e) => {
                // On blur, ensure we have a valid value or reset to default
                const value = e.target.value
                if (value === "" || parseInt(value) <= 0) {
                  setMaxStocksInput("3")
                  handleChange("max_stocks", 3)
                }
              }}
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
              value={rebalanceIntervalInput}
              onChange={(e) => {
                const value = e.target.value
                setRebalanceIntervalInput(value)
                // Update formData only if value is valid number
                const numValue = parseInt(value)
                if (!isNaN(numValue) && numValue > 0) {
                  handleChange("rebalance_interval_weeks", numValue)
                }
              }}
              onBlur={(e) => {
                // On blur, ensure we have a valid value or reset to default
                const value = e.target.value
                if (value === "" || parseInt(value) <= 0) {
                  setRebalanceIntervalInput("2")
                  handleChange("rebalance_interval_weeks", 2)
                }
              }}
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
                type="text"
                placeholder="yyyy/mm/dd"
                value={formatDateForDisplay(formData.date_start)}
                onChange={(e) => {
                  const value = e.target.value
                  // Allow typing yyyy/mm/dd format
                  const dateInputPattern = new RegExp("^\\d{0,4}(/\\d{0,2})?(/\\d{0,2})?$")
                  if (value === "" || dateInputPattern.test(value)) {
                    handleDateChange("date_start", value)
                  }
                }}
                onBlur={(e) => {
                  const value = e.target.value
                  if (value && !isValidDate(value)) {
                    // Try to fix common issues
                    const fixed = value.replace(/[^\d/]/g, "")
                    if (isValidDate(fixed)) {
                      handleDateChange("date_start", fixed)
                    } else {
                      // Reset to default if invalid
                      const date = new Date()
                      date.setFullYear(date.getFullYear() - 1)
                      handleDateChange("date_start", formatDateForDisplay(date.toISOString().split("T")[0]))
                    }
                  }
                }}
                required
              />
              <p className="text-xs text-muted-foreground">Simulation start date (yyyy/mm/dd)</p>
            </div>

            <div className="space-y-2">
              <label htmlFor="date_end" className="text-sm font-medium">
                End Date
              </label>
              <Input
                id="date_end"
                type="text"
                placeholder="yyyy/mm/dd"
                value={formatDateForDisplay(formData.date_end)}
                onChange={(e) => {
                  const value = e.target.value
                  // Allow typing yyyy/mm/dd format
                  const dateInputPattern = new RegExp("^\\d{0,4}(/\\d{0,2})?(/\\d{0,2})?$")
                  if (value === "" || dateInputPattern.test(value)) {
                    handleDateChange("date_end", value)
                  }
                }}
                onBlur={(e) => {
                  const value = e.target.value
                  if (value && !isValidDate(value)) {
                    // Try to fix common issues
                    const fixed = value.replace(/[^\d/]/g, "")
                    if (isValidDate(fixed)) {
                      handleDateChange("date_end", fixed)
                    } else {
                      // Reset to default if invalid
                      handleDateChange("date_end", formatDateForDisplay(new Date().toISOString().split("T")[0]))
                    }
                  }
                }}
                required
              />
              <p className="text-xs text-muted-foreground">Simulation end date (yyyy/mm/dd)</p>
            </div>
          </div>

          {/* Rule */}
          <div className="space-y-2">
            <label htmlFor="rule" className="text-sm font-medium">
              Selection Rule
            </label>
            <textarea
              ref={textareaRef}
              id="rule"
              value={formData.rule}
              onChange={(e) => handleChange("rule", e.target.value)}
              required
              rows={8}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none font-mono"
              placeholder="change_3m_pct > 10 AND biggest_biweekly_drop_pct > 1"
            />
            <div className="text-xs text-muted-foreground space-y-2">
              <p>
                Python expression that evaluates to True/False for stock selection. Click on a variable name to insert it into the rule:
              </p>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[200px]">Variable</TableHead>
                      <TableHead className="w-[80px]">Type</TableHead>
                      <TableHead>Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("weeks_above_1_week_ago")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          weeks_above_1_week_ago
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">int</TableCell>
                      <TableCell className="text-xs">Number of weeks where closing price was higher than 1 week prior</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("weeks_above_2_weeks_ago")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          weeks_above_2_weeks_ago
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">int</TableCell>
                      <TableCell className="text-xs">Number of weeks where closing price was higher than 2 weeks prior</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("weeks_above_4_weeks_ago")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          weeks_above_4_weeks_ago
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">int</TableCell>
                      <TableCell className="text-xs">Number of weeks where closing price was higher than 4 weeks prior</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("biggest_weekly_jump_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          biggest_weekly_jump_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Largest week-over-week percentage increase</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("biggest_weekly_drop_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          biggest_weekly_drop_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Largest week-over-week percentage decrease</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("biggest_biweekly_jump_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          biggest_biweekly_jump_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Largest biweekly (2-week) percentage increase</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("biggest_biweekly_drop_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          biggest_biweekly_drop_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Largest biweekly (2-week) percentage decrease</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("biggest_monthly_jump_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          biggest_monthly_jump_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Largest monthly (4-week) percentage increase</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("biggest_monthly_drop_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          biggest_monthly_drop_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Largest monthly (4-week) percentage decrease</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("change_1y_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          change_1y_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Percentage change over 1 year (52 weeks)</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("change_6m_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          change_6m_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Percentage change over 6 months (26 weeks)</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("change_3m_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          change_3m_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Percentage change over 3 months (13 weeks)</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("change_1m_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          change_1m_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Percentage change over 1 month (4 weeks)</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("total_weeks")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          total_weeks
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">int</TableCell>
                      <TableCell className="text-xs">Total number of weeks analyzed</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("linear_slope_pct")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          linear_slope_pct
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Linear trend slope as percentage of starting price per week</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("linear_r_squared")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          linear_r_squared
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">R² value (0-1) indicating how well the price data fits the trend line (higher = more consistent trend)</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("log_slope")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          log_slope
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">Annualized trend slope</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => insertVariableAtCursor("log_r_squared")}
                          className="font-mono text-xs text-primary hover:underline cursor-pointer"
                        >
                          log_r_squared
                        </button>
                      </TableCell>
                      <TableCell className="text-xs">float</TableCell>
                      <TableCell className="text-xs">R² value (0-1) indicating how well the price data fits the trend line (higher = more consistent trend)</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </div>
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
