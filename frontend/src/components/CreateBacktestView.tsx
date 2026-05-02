import { useState, useEffect, useRef } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
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
import { dateFormat } from "@/lib/utils"

type StockIndex = "SP500" | "NASDAQ"

const DEFAULT_RANKING = "change_pct_13w / return_std_52w"

const RULE_VARIABLES: { name: string; type: string; description: string }[] = [
  { name: "max_jump_pct_1w", type: "float", description: "Maximum 1-week percentage increase" },
  { name: "max_drop_pct_1w", type: "float", description: "Maximum 1-week percentage decrease" },
  { name: "max_jump_pct_2w", type: "float", description: "Maximum 2-week percentage increase" },
  { name: "max_drop_pct_2w", type: "float", description: "Maximum 2-week percentage decrease" },
  { name: "max_jump_pct_4w", type: "float", description: "Maximum 4-week percentage increase" },
  { name: "max_drop_pct_4w", type: "float", description: "Maximum 4-week percentage decrease" },
  { name: "change_pct_52w", type: "float", description: "Percentage change over 52 weeks (1 year)" },
  { name: "change_pct_26w", type: "float", description: "Percentage change over 26 weeks" },
  { name: "change_pct_13w", type: "float", description: "Percentage change over 13 weeks" },
  { name: "change_pct_4w", type: "float", description: "Percentage change over 4 weeks" },
  { name: "change_pct_2w", type: "float", description: "Percentage change over 2 weeks" },
  { name: "change_pct_1w", type: "float", description: "Percentage change over 1 week" },
  { name: "total_weeks", type: "int", description: "Total number of weeks analyzed" },
  { name: "slope_pct_13w", type: "float", description: "Linear trend slope over last 13 weeks, % of starting price per week" },
  { name: "slope_pct_26w", type: "float", description: "Linear trend slope over last 26 weeks, % of starting price per week" },
  { name: "slope_pct_52w", type: "float", description: "Linear trend slope over last 52 weeks, % of starting price per week" },
  { name: "r_squared_4w", type: "float", description: "R² of 4-week regression (0-1, higher = more consistent very-short-term trend)" },
  { name: "r_squared_13w", type: "float", description: "R² of 13-week regression (0-1, higher = more consistent short-term trend)" },
  { name: "r_squared_26w", type: "float", description: "R² of 26-week regression (0-1, higher = more consistent medium-term trend)" },
  { name: "r_squared_52w", type: "float", description: "R² of 52-week regression (0-1, higher = more consistent long-term trend)" },
  { name: "log_slope_13w", type: "float", description: "Log-regression slope over last 13 weeks (compounded growth rate per week)" },
  { name: "log_r_squared_13w", type: "float", description: "R² of 13-week log regression (consistency of compounded growth)" },
  { name: "log_slope_26w", type: "float", description: "Log-regression slope over last 26 weeks (compounded growth rate per week)" },
  { name: "log_r_squared_26w", type: "float", description: "R² of 26-week log regression (consistency of compounded growth)" },
  { name: "log_slope_52w", type: "float", description: "Log-regression slope over last 52 weeks (compounded growth rate per week)" },
  { name: "log_r_squared_52w", type: "float", description: "R² of 52-week log regression (consistency of compounded growth)" },
  { name: "return_std_52w", type: "float", description: "Standard deviation of weekly returns over 52 weeks (volatility)" },
  { name: "downside_std_52w", type: "float", description: "Standard deviation of negative weekly returns over 52 weeks (downside volatility)" },
  { name: "max_drawdown_pct_4w", type: "float", description: "Max peak-to-trough decline over last 4 weeks (positive %)" },
  { name: "max_drawdown_pct_13w", type: "float", description: "Max peak-to-trough decline over last 13 weeks (positive %)" },
  { name: "max_drawdown_pct_26w", type: "float", description: "Max peak-to-trough decline over last 26 weeks (positive %)" },
  { name: "max_drawdown_pct_52w", type: "float", description: "Max peak-to-trough decline over last 52 weeks (positive %). Use < to filter." },
  { name: "pct_weeks_positive_4w", type: "float", description: "Fraction of up-weeks over last 4 weeks (0.0–1.0)" },
  { name: "pct_weeks_positive_13w", type: "float", description: "Fraction of up-weeks over last 13 weeks (0.0–1.0)" },
  { name: "pct_weeks_positive_26w", type: "float", description: "Fraction of up-weeks over last 26 weeks (0.0–1.0)" },
  { name: "pct_weeks_positive_52w", type: "float", description: "Fraction of up-weeks over last 52 weeks (0.0–1.0). Use > 0.55 for stable risers." },
  { name: "acceleration_pct_13w", type: "float", description: "Slope of 4-week change over last 13 weeks (momentum acceleration)" },
  { name: "from_high_pct_4w", type: "float", description: "Distance below 4-week high (negative %); closer to 0 = near recent high" },
  // Moving average structure (price vs SMA, %)
  { name: "price_vs_ma20_pct", type: "float", description: "Current price vs 20-day SMA in % ((price/MA - 1) * 100). >0 = above MA" },
  { name: "price_vs_ma50_pct", type: "float", description: "Current price vs 50-day SMA in %. >0 = above MA (medium-term uptrend)" },
  { name: "price_vs_ma100_pct", type: "float", description: "Current price vs 100-day SMA in %. >0 = above MA" },
  { name: "price_vs_ma200_pct", type: "float", description: "Current price vs 200-day SMA in %. >0 = above MA (classic long-term uptrend)" },
  { name: "ma50_vs_ma200_pct", type: "float", description: "50-day SMA vs 200-day SMA in %. >0 = golden-cross territory" },
]

type StopLossMode = "none" | "percent" | "ma_percent"
type StopLossMaPeriod = 20 | 50 | 100 | 200

const STOP_LOSS_MA_PERIODS: StopLossMaPeriod[] = [20, 50, 100, 200]

interface StopLossPayload {
  type: "percent" | "ma_percent"
  value: number
  ma_period?: number
}

interface BacktestRequest {
  max_stocks: number
  rebalance_interval_weeks: number
  date_start: string // ISO datetime string
  date_end: string // ISO datetime string
  rule: string
  ranking: string
  index: StockIndex
  stop_loss?: StopLossPayload | null
}

export function CreateBacktestView() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Initialize form data from URL parameters if available, otherwise use defaults
  const getInitialFormData = (): BacktestRequest => {
    const maxStocks = searchParams.get("max_stocks")
    const rebalanceInterval = searchParams.get("rebalance_interval_weeks")
    const dateStart = searchParams.get("date_start") || ""
    const dateEnd = searchParams.get("date_end") || ""
    const rule = searchParams.get("rule") || ""
    const ranking = searchParams.get("ranking") || DEFAULT_RANKING
    const index = (searchParams.get("index") as StockIndex) || "SP500"

    return {
      max_stocks: maxStocks ? parseInt(maxStocks) : 3,
      rebalance_interval_weeks: rebalanceInterval ? parseInt(rebalanceInterval) : 2,
      date_start: dateStart ? dateStart.replace(/\//g, "-") : "", // Convert yyyy/mm/dd to yyyy-mm-dd
      date_end: dateEnd ? dateEnd.replace(/\//g, "-") : "",
      rule: rule,
      ranking: ranking,
      index: index,
    }
  }
  
  const [formData, setFormData] = useState<BacktestRequest>(getInitialFormData())
  
  // Store string values for numeric inputs to allow empty state
  const [maxStocksInput, setMaxStocksInput] = useState<string>(() => {
    const val = searchParams.get("max_stocks")
    return val || formData.max_stocks.toString()
  })
  const [rebalanceIntervalInput, setRebalanceIntervalInput] = useState<string>(() => {
    const val = searchParams.get("rebalance_interval_weeks")
    return val || formData.rebalance_interval_weeks.toString()
  })
  // Store raw string values for date inputs to allow free typing
  const [dateStartInput, setDateStartInput] = useState<string>(() => {
    const val = searchParams.get("date_start")
    return val || ""
  })
  const [dateEndInput, setDateEndInput] = useState<string>(() => {
    const val = searchParams.get("date_end")
    return val || ""
  })
  // Stop-loss state. Stop level is fixed at buy time (static; not trailing).
  const [stopLossMode, setStopLossMode] = useState<StopLossMode>(() => {
    const t = searchParams.get("stop_loss_type")
    return t === "percent" || t === "ma_percent" ? t : "none"
  })
  const [stopLossValueInput, setStopLossValueInput] = useState<string>(() => {
    return searchParams.get("stop_loss_value") || ""
  })
  const [stopLossMaPeriod, setStopLossMaPeriod] = useState<StopLossMaPeriod>(() => {
    const p = parseInt(searchParams.get("stop_loss_ma_period") || "", 10)
    return STOP_LOSS_MA_PERIODS.includes(p as StopLossMaPeriod) ? (p as StopLossMaPeriod) : 50
  })
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
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

      // Send naive midnight datetimes (no timezone marker) so backend parses
      // them identically to CLI `datetime.strptime(..., "%Y-%m-%d")`.
      const dateStart = `${formData.date_start}T00:00:00`
      const dateEnd = `${formData.date_end}T00:00:00`

      let stopLoss: StopLossPayload | null = null
      if (stopLossMode !== "none") {
        const value = parseFloat(stopLossValueInput)
        if (isNaN(value) || value <= 0) {
          throw new Error("Stop loss value must be a positive number")
        }
        stopLoss =
          stopLossMode === "percent"
            ? { type: "percent", value }
            : { type: "ma_percent", value, ma_period: stopLossMaPeriod }
      }

      const response = await fetch("/api/backtest", {
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
          stop_loss: stopLoss,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to create backtest" }))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setLoading(false)
      if (result.backtest_id) {
        navigate(`/backtest/${result.backtest_id}`)
        return
      }
      navigate("/backtest")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create backtest")
      setLoading(false)
    }
  }

  const handleChange = (field: keyof BacktestRequest, value: string | number) => {
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

    const defaultStart = getDefaultStartDate()
    const defaultEnd = getDefaultEndDate()
    
    setFormData((prev) => ({
      ...prev,
      date_start: prev.date_start || defaultStart,
      date_end: prev.date_end || defaultEnd,
    }))
    
    // Initialize input strings with formatted dates only if empty
    setDateStartInput((prev) => prev || dateFormat(defaultStart))
    setDateEndInput((prev) => prev || dateFormat(defaultEnd))
  }, [])

  return (
    <div className="relative mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8">
        <h1 className="mb-2 text-3xl font-semibold tracking-tight text-foreground">
          Create Backtest
        </h1>
        <p className="text-muted-foreground">
          Configure and run a new investment strategy backtest
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
                value={dateStartInput}
                onChange={(e) => {
                  setDateStartInput(e.target.value)
                }}
                onBlur={(e) => {
                  const value = e.target.value
                  if (value && !isValidDate(value)) {
                    // Try to fix common issues
                    const fixed = value.replace(/[^\d/]/g, "")
                    if (isValidDate(fixed)) {
                      setDateStartInput(fixed)
                      handleDateChange("date_start", fixed)
                    } else {
                      // Reset to default if invalid
                      const date = new Date()
                      date.setFullYear(date.getFullYear() - 1)
                      const defaultDate = dateFormat(date.toISOString().split("T")[0])
                      setDateStartInput(defaultDate)
                      handleDateChange("date_start", defaultDate)
                    }
                  } else if (value && isValidDate(value)) {
                    // Update formData with valid date
                    handleDateChange("date_start", value)
                  }
                }}
                required
              />
              <p className="text-xs text-muted-foreground">Backtest start date (yyyy/mm/dd)</p>
            </div>

            <div className="space-y-2">
              <label htmlFor="date_end" className="text-sm font-medium">
                End Date
              </label>
              <Input
                id="date_end"
                type="text"
                placeholder="yyyy/mm/dd"
                value={dateEndInput}
                onChange={(e) => {
                  setDateEndInput(e.target.value)
                }}
                onBlur={(e) => {
                  const value = e.target.value
                  if (value && !isValidDate(value)) {
                    // Try to fix common issues
                    const fixed = value.replace(/[^\d/]/g, "")
                    if (isValidDate(fixed)) {
                      setDateEndInput(fixed)
                      handleDateChange("date_end", fixed)
                    } else {
                      // Reset to default if invalid
                      const defaultDate = dateFormat(new Date().toISOString().split("T")[0])
                      setDateEndInput(defaultDate)
                      handleDateChange("date_end", defaultDate)
                    }
                  } else if (value && isValidDate(value)) {
                    // Update formData with valid date
                    handleDateChange("date_end", value)
                  }
                }}
                required
              />
              <p className="text-xs text-muted-foreground">Backtest end date (yyyy/mm/dd)</p>
            </div>
          </div>

          {/* Ranking */}
          <div className="space-y-2">
            <label htmlFor="ranking" className="text-sm font-medium">
              Ranking Expression
            </label>
            <Input
              id="ranking"
              type="text"
              value={formData.ranking}
              onChange={(e) => handleChange("ranking", e.target.value)}
              required
              className="font-mono"
              placeholder={DEFAULT_RANKING}
            />
            <p className="text-xs text-muted-foreground">
              Expression used to rank stocks that pass the rule. Higher value = higher priority.
            </p>
          </div>

          {/* Stop Loss */}
          <div className="space-y-2">
            <label htmlFor="stop_loss_mode" className="text-sm font-medium">
              Stop Loss
            </label>
            <Select
              value={stopLossMode}
              onValueChange={(value) => setStopLossMode(value as StopLossMode)}
            >
              <SelectTrigger id="stop_loss_mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                <SelectItem value="percent">% below buy price</SelectItem>
                <SelectItem value="ma_percent">% of MA at buy time</SelectItem>
              </SelectContent>
            </Select>
            {stopLossMode !== "none" && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {stopLossMode === "ma_percent" && (
                  <div className="space-y-1">
                    <label htmlFor="stop_loss_ma_period" className="text-xs font-medium">
                      MA period
                    </label>
                    <Select
                      value={stopLossMaPeriod.toString()}
                      onValueChange={(v) =>
                        setStopLossMaPeriod(parseInt(v) as StopLossMaPeriod)
                      }
                    >
                      <SelectTrigger id="stop_loss_ma_period">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STOP_LOSS_MA_PERIODS.map((p) => (
                          <SelectItem key={p} value={p.toString()}>
                            MA{p}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="space-y-1">
                  <label htmlFor="stop_loss_value" className="text-xs font-medium">
                    {stopLossMode === "percent"
                      ? "% below buy price"
                      : "% of MA at buy"}
                  </label>
                  <Input
                    id="stop_loss_value"
                    type="number"
                    min="0"
                    step="0.5"
                    value={stopLossValueInput}
                    onChange={(e) => setStopLossValueInput(e.target.value)}
                    placeholder={stopLossMode === "percent" ? "5" : "95"}
                  />
                </div>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Per-position stop loss, fixed at buy time. Triggers when daily low ≤
              stop price; sells at the stop price.
            </p>
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
              placeholder="change_pct_13w > 10 AND max_drawdown_pct_52w < 20 AND pct_weeks_positive_52w > 0.55"
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
                    {RULE_VARIABLES.map((v) => (
                      <TableRow key={v.name}>
                        <TableCell>
                          <button
                            type="button"
                            onClick={() => insertVariableAtCursor(v.name)}
                            className="font-mono text-xs text-primary hover:underline cursor-pointer"
                          >
                            {v.name}
                          </button>
                        </TableCell>
                        <TableCell className="text-xs">{v.type}</TableCell>
                        <TableCell className="text-xs">{v.description}</TableCell>
                      </TableRow>
                    ))}
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
            onClick={() => navigate("/backtest")}
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
              "Create Backtest"
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
