import { useEffect, useState, useMemo, useCallback } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { ArrowUp, ArrowDown, Copy, Check } from "lucide-react"
import type { Simulation, Investment } from "@/types/simulation"
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${day}/${month}/${year}`
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
}

interface Snp500Price {
  date: string
  price: number
}

interface ChartDataPoint {
  date: string
  dateRaw: string
  balance: number
  snp500Balance?: number
  investments: Investment[]
  rebalanceIndex?: number
}

function CustomTooltip(props: any) {
  const { active, payload, label } = props
  
  if (!active || !payload || !payload.length) {
    return null
  }

  const data = payload[0].payload as ChartDataPoint
  const investments = data.investments || []
  
  // Find S&P 500 value from payload
  const snp500Payload = payload.find((p: any) => p.dataKey === "snp500Balance")
  const snp500Balance = snp500Payload?.value

  return (
    <div className="rounded-lg border bg-card p-3 shadow-lg">
      <p className="font-semibold mb-2 text-sm">{label}</p>
      <p className="text-sm mb-2">
        Portfolio Balance: <span className="font-medium">{formatCurrency(data.balance)}</span>
      </p>
      {snp500Balance !== undefined && (
        <p className="text-sm mb-2">
          S&P 500: <span className="font-medium">{formatCurrency(snp500Balance)}</span>
        </p>
      )}
      {investments.length > 0 && (
        <div className="mt-2 pt-2 border-t">
          <div className="space-y-1.5">
            {investments.map((inv, idx) => (
              <div key={idx} className="text-xs">
                <div className="font-medium mb-0.5">{inv.symbol}</div>
                <div className="pl-2 space-y-0.5 text-muted-foreground">
                  <div>BUY {inv.position.toFixed(0)}@{inv.buy_price.toFixed(2)}</div>
                  <div>SELL {inv.position.toFixed(0)}@{inv.sell_price.toFixed(2)}</div>
                  <div className={inv.profit_pct >= 0 ? "text-green-600" : "text-red-600"}>
                    Profit {formatCurrency(inv.profit)} ({formatPercent(inv.profit_pct)})
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

type SortColumn = "buy_date" | "profit" | "profit_pct" | null
type SortDirection = "asc" | "desc" | null

export function SimulationView() {
  const { file: urlFile } = useParams<{ file?: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [simulations, setSimulations] = useState<string[]>([])
  const [selectedSimulation, setSelectedSimulation] = useState<string>("")
  const [simulationData, setSimulationData] = useState<Simulation | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [ruleCopied, setRuleCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tableView, setTableView] = useState<"investment" | "rebalance">("investment")
  const [selectedRebalanceIndex, setSelectedRebalanceIndex] = useState<number | null>(null)
  const [sortConfig, setSortConfig] = useState<{ column: SortColumn; direction: SortDirection }>({
    column: null,
    direction: null,
  })
  const [snp500Prices, setSnp500Prices] = useState<Snp500Price[]>([])

  // Load available simulations
  useEffect(() => {
    fetch("/api/simulations")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load simulations list")
        return res.json()
      })
      .then((files: string[]) => {
        if (files.length === 0) {
          throw new Error("No simulation files available")
        }
        setSimulations(files)
        // Use URL file if provided and valid, otherwise use the most recent file
        if (urlFile && files.includes(urlFile)) {
          setSelectedSimulation(urlFile)
        } else {
          setSelectedSimulation(files[0])
          // Update URL if no file in URL or invalid file
          if (!urlFile || !files.includes(urlFile)) {
            navigate(`/simulation/${files[0]}`, { replace: true })
          }
        }
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  // Handle URL file changes
  useEffect(() => {
    if (urlFile && simulations.includes(urlFile) && selectedSimulation !== urlFile) {
      setSelectedSimulation(urlFile)
    }
  }, [urlFile, simulations, selectedSimulation, navigate])

  // Load S&P 500 price data
  useEffect(() => {
    let cancelled = false

    fetch("/api/snp500")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load S&P 500 data")
        return res.json()
      })
      .then((data: Snp500Price[]) => {
        if (!cancelled) {
          setSnp500Prices(data)
        }
      })
      .catch((err) => {
        console.error("Failed to load S&P 500 data:", err)
        // Don't set error state, just log it - S&P 500 is optional
      })

    return () => {
      cancelled = true
    }
  }, [])

  // Load simulation data when selected simulation changes
  useEffect(() => {
    if (!selectedSimulation) return

    let cancelled = false

    requestAnimationFrame(() => {
      if (!cancelled) {
        setLoadingData(true)
        setError(null)
      }
    })

    fetch(`/api/simulations/${selectedSimulation}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load simulation data")
        return res.json()
      })
      .then((json: Simulation) => {
        if (!cancelled) {
          setSimulationData(json)
          setLoadingData(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
          setLoadingData(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedSimulation])

  // Sync URL query param with selectedRebalanceIndex when simulationData loads or URL changes
  useEffect(() => {
    if (!simulationData) return

    const rebalanceDate = searchParams.get("rebalance")
    
    if (rebalanceDate) {
      // Find the index of the rebalance with matching date
      const index = simulationData.rebalance_history.findIndex(
        (r) => r.date === rebalanceDate
      )
      if (index !== -1) {
        // Only update if different to avoid loops
        setSelectedRebalanceIndex((prev) => prev !== index ? index : prev)
      } else {
        // Invalid date in URL, remove it
        const newSearchParams = new URLSearchParams(searchParams)
        newSearchParams.delete("rebalance")
        setSearchParams(newSearchParams, { replace: true })
        setSelectedRebalanceIndex(null)
      }
    } else {
      // URL has no rebalance param, clear selection if set
      setSelectedRebalanceIndex((prev) => prev !== null ? null : prev)
    }
  }, [simulationData, searchParams, setSearchParams])

  const handleSort = useCallback((column: SortColumn) => {
    setSortConfig((prev) => {
      if (prev.column === column) {
        if (prev.direction === "asc") return { column, direction: "desc" }
        if (prev.direction === "desc") return { column: null, direction: null }
      }
      return { column, direction: "asc" }
    })
  }, [])

  const handleCopyRule = useCallback(async () => {
    if (!simulationData?.rule_ref) return
    
    try {
      await navigator.clipboard.writeText(simulationData.rule_ref)
      setRuleCopied(true)
      setTimeout(() => setRuleCopied(false), 2000)
    } catch (err) {
      console.error("Failed to copy rule:", err)
    }
  }, [simulationData?.rule_ref])

  // Flatten all investments from all rebalances
  const allInvestments = useMemo(() => {
    if (!simulationData) return []
    return simulationData.rebalance_history.flatMap(rebalance => rebalance.investments)
  }, [simulationData])

  const sortedInvestments = useMemo(() => {
    if (!simulationData) return []
    
    const investments = [...allInvestments]
    
    if (!sortConfig.column || !sortConfig.direction) {
      return investments
    }

    return investments.sort((a, b) => {
      let aVal: number | string
      let bVal: number | string

      switch (sortConfig.column) {
        case "buy_date":
          aVal = new Date(a.buy_date).getTime()
          bVal = new Date(b.buy_date).getTime()
          break
        case "profit":
          aVal = a.profit
          bVal = b.profit
          break
        case "profit_pct":
          aVal = a.profit_pct
          bVal = b.profit_pct
          break
        default:
          return 0
      }

      if (sortConfig.direction === "asc") {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      } else {
        return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
      }
    })
  }, [allInvestments, sortConfig, simulationData])

  const handleChartClick = useCallback((data: any) => {
    if (data && data.activePayload && data.activePayload.length > 0) {
      const payload = data.activePayload[0].payload
      const index = payload.rebalanceIndex
      if (index !== undefined && index !== null && simulationData) {
        const newIndex = selectedRebalanceIndex === index ? null : index
        setSelectedRebalanceIndex(newIndex)
        
        // Update URL query param
        const newSearchParams = new URLSearchParams(searchParams)
        if (newIndex !== null) {
          const rebalance = simulationData.rebalance_history[newIndex]
          if (rebalance) {
            newSearchParams.set("rebalance", rebalance.date)
          }
        } else {
          newSearchParams.delete("rebalance")
        }
        setSearchParams(newSearchParams)
      }
    }
  }, [simulationData, selectedRebalanceIndex, searchParams, setSearchParams])

  // Custom dot component that handles clicks
  const CustomDot = useCallback((props: any) => {
    const { cx, cy, payload } = props
    if (cx == null || cy == null) return null
    
    const handleClick = (e: any) => {
      e.stopPropagation()
      e.preventDefault()
      const index = payload?.rebalanceIndex
      if (index !== undefined && index !== null && simulationData) {
        const newIndex = selectedRebalanceIndex === index ? null : index
        setSelectedRebalanceIndex(newIndex)
        
        // Update URL query param
        const newSearchParams = new URLSearchParams(searchParams)
        if (newIndex !== null) {
          const rebalance = simulationData.rebalance_history[newIndex]
          if (rebalance) {
            newSearchParams.set("rebalance", rebalance.date)
          }
        } else {
          newSearchParams.delete("rebalance")
        }
        setSearchParams(newSearchParams)
      }
    }
    
    const handleMouseDown = (e: any) => {
      e.stopPropagation()
      handleClick(e)
    }
    
    return (
      <g 
        onClick={handleClick}
        onMouseDown={handleMouseDown}
        style={{ cursor: 'pointer' }}
      >
        {/* Larger invisible circle for easier clicking */}
        <circle
          cx={cx}
          cy={cy}
          r={10}
          fill="transparent"
          stroke="transparent"
          strokeWidth={0}
          style={{ pointerEvents: 'all' }}
        />
        {/* Visible dot */}
        <circle
          cx={cx}
          cy={cy}
          r={4}
          fill="hsl(var(--primary))"
          style={{ pointerEvents: 'none' }}
        />
      </g>
    )
  }, [simulationData, selectedRebalanceIndex, searchParams, setSearchParams])

  const chartData = useMemo(() => {
    if (!simulationData) return []
    
    // Helper function to normalize date strings (remove time component if present)
    const normalizeDate = (dateStr: string): string => {
      return dateStr.split('T')[0]
    }
    
    // Find the S&P 500 price on the start date to normalize
    const startDate = normalizeDate(simulationData.date_start)
    let startSnp500Price: number | undefined
    
    // Try exact match first
    const exactStartMatch = snp500Prices.find(p => normalizeDate(p.date) === startDate)
    if (exactStartMatch) {
      startSnp500Price = exactStartMatch.price
    } else {
      // Find the nearest price before or on the start date
      const startDateParsed = new Date(startDate)
      const pricesBeforeStart = snp500Prices.filter(p => {
        const pDate = new Date(p.date)
        return pDate <= startDateParsed
      })
      if (pricesBeforeStart.length > 0) {
        // Prices are sorted oldest first, so get the last one
        startSnp500Price = pricesBeforeStart[pricesBeforeStart.length - 1].price
      }
    }
    
    // If we still don't have a start price, find the closest date
    if (!startSnp500Price && snp500Prices.length > 0) {
      const startDateParsed = new Date(startDate)
      // Find the closest date (before or after)
      let closestPrice = snp500Prices[0]
      let minDiff = Math.abs(new Date(closestPrice.date).getTime() - startDateParsed.getTime())
      
      for (const price of snp500Prices) {
        const diff = Math.abs(new Date(price.date).getTime() - startDateParsed.getTime())
        if (diff < minDiff) {
          minDiff = diff
          closestPrice = price
        }
      }
      startSnp500Price = closestPrice.price
    }
    
    return simulationData.rebalance_history.map((rebalance, index) => {
      // Find S&P 500 price for this rebalance date (or nearest before)
      let snp500Price: number | undefined
      const rebalanceDate = normalizeDate(rebalance.date)
      
      // Try exact match first
      const exactMatch = snp500Prices.find(p => normalizeDate(p.date) === rebalanceDate)
      if (exactMatch) {
        snp500Price = exactMatch.price
      } else {
        // Find the nearest price before this date
        const rebalanceDateParsed = new Date(rebalanceDate)
        const pricesBefore = snp500Prices.filter(p => {
          const pDate = new Date(p.date)
          return pDate <= rebalanceDateParsed
        })
        if (pricesBefore.length > 0) {
          // Prices are sorted oldest first, so get the last one
          snp500Price = pricesBefore[pricesBefore.length - 1].price
        } else {
          // If no price before, use the first available price
          snp500Price = snp500Prices[0]?.price
        }
      }
      
      // Normalize S&P 500 price to match initial balance
      let snp500Balance: number | undefined
      if (snp500Price && startSnp500Price && startSnp500Price > 0 && simulationData.initial_balance) {
        snp500Balance = (snp500Price / startSnp500Price) * simulationData.initial_balance
      }
      
      return {
        date: formatDate(rebalance.date),
        dateRaw: rebalance.date,
        balance: rebalance.balance,
        snp500Balance,
        investments: rebalance.investments,
        rebalanceIndex: index,
      }
    })
  }, [simulationData, snp500Prices])
  
  // Check if we have any valid S&P 500 balance data
  const hasSnp500Data = useMemo(() => {
    return chartData.some(point => point.snp500Balance !== undefined && point.snp500Balance > 0)
  }, [chartData])

  const selectedRebalance = useMemo(() => {
    return selectedRebalanceIndex !== null && simulationData
      ? simulationData.rebalance_history[selectedRebalanceIndex]
      : null
  }, [selectedRebalanceIndex, simulationData])

  const totalProfit = useMemo(() => simulationData?.profit || 0, [simulationData])
  const totalProfitPct = useMemo(() => {
    return simulationData?.profit_pct ? simulationData.profit_pct * 100 : 0
  }, [simulationData])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading simulations...</p>
        </div>
      </div>
    )
  }

  if (error && !simulationData) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
          <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
          <p className="text-muted-foreground">{error ?? "No data available"}</p>
          <p className="mt-4 text-sm text-muted-foreground">
            Make sure the API server is running and simulation files are available
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative mx-auto max-w-[2000px] px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-8 text-center">
          <h1 className="mb-4 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            Simulation Results
          </h1>
          <div className="mb-4 flex items-center justify-center gap-4">
            <label htmlFor="simulation-select" className="text-sm font-medium text-muted-foreground">
              Select Simulation:
            </label>
            <Select value={selectedSimulation} onValueChange={(value) => {
              setSelectedSimulation(value)
              navigate(`/simulation/${value}`)
            }}>
              <SelectTrigger id="simulation-select" className="w-[300px]">
                <SelectValue placeholder="Select a simulation" />
              </SelectTrigger>
              <SelectContent>
                {simulations.map((sim) => (
                  <SelectItem key={sim} value={sim}>
                    {sim}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {simulationData && (
            <div className="flex flex-col items-center gap-4">
              <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
                <span>
                  Period: {formatDate(simulationData.date_start)} - {formatDate(simulationData.date_end)}
                </span>
                <span>•</span>
                <span>Initial Balance: {formatCurrency(simulationData.initial_balance)}</span>
                <span>•</span>
                <span>
                  Final Balance:{" "}
                  {formatCurrency(
                    simulationData.rebalance_history[simulationData.rebalance_history.length - 1]?.balance ||
                      simulationData.initial_balance
                  )}
                </span>
                <span>•</span>
                <span className={totalProfitPct >= 0 ? "text-green-600" : "text-red-600"}>
                  Total Return: {formatPercent(totalProfitPct)} ({formatCurrency(totalProfit)})
                </span>
              </div>
              {simulationData.rule_ref && (
                <div className="w-full max-w-2xl">
                  <div className="flex gap-2 items-start">
                    <textarea
                      readOnly
                      value={simulationData.rule_ref}
                      className="flex min-h-[60px] w-full rounded-md border border-input bg-muted px-3 py-2 text-sm font-mono shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                      rows={Math.min(Math.max(simulationData.rule_ref.split('\n').length, 2), 6)}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={handleCopyRule}
                      className="shrink-0"
                      title="Copy rule to clipboard"
                    >
                      {ruleCopied ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </header>

        {/* Main Content */}
        <main className="space-y-8">
          {loadingData ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-muted-foreground">Loading simulation data...</p>
              </div>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
              <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
              <p className="text-muted-foreground">{error}</p>
            </div>
          ) : simulationData ? (
            <>
              {/* Balance History Chart */}
              <div className="rounded-lg border bg-card p-6">
                <h2 className="mb-4 text-2xl font-semibold">Balance History</h2>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart 
                    data={chartData} 
                    onClick={handleChartClick}
                    style={{ cursor: 'default' }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12 }}
                      style={{ fontSize: 12 }}
                    />
                    <YAxis 
                      tickFormatter={(value) => formatCurrency(value)} 
                      tick={{ fontSize: 12 }}
                      style={{ fontSize: 12 }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line
                      type="monotone"
                      dataKey="balance"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={CustomDot}
                      activeDot={{ 
                        r: 8, 
                        cursor: "pointer", 
                        onClick: (_e: any, payload: any) => {
                          const index = payload?.payload?.rebalanceIndex
                          if (index !== undefined && index !== null && simulationData) {
                            const newIndex = selectedRebalanceIndex === index ? null : index
                            setSelectedRebalanceIndex(newIndex)
                            
                            // Update URL query param
                            const newSearchParams = new URLSearchParams(searchParams)
                            if (newIndex !== null) {
                              const rebalance = simulationData.rebalance_history[newIndex]
                              if (rebalance) {
                                newSearchParams.set("rebalance", rebalance.date)
                              }
                            } else {
                              newSearchParams.delete("rebalance")
                            }
                            setSearchParams(newSearchParams)
                          }
                        }
                      }}
                      name="Portfolio Balance"
                    />
                    {hasSnp500Data && (
                      <Line
                        type="monotone"
                        dataKey="snp500Balance"
                        stroke="#8884d8"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={false}
                        name="S&P 500"
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
                <p className="mt-2 text-xs text-muted-foreground text-center">
                  Click on a data point to view rebalance details
                </p>
              </div>

              {/* Selected Rebalance Detail Section */}
              {selectedRebalance && (
                <div className="rounded-lg border bg-card p-6">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-2xl font-semibold">
                      Rebalance Details - {formatDate(selectedRebalance.date)}
                    </h2>
                    <div className="flex items-center gap-2">
                      {selectedRebalance.analysis_ref && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            // Remove .json extension if present, as API expects filename without extension
                            const file = selectedRebalance.analysis_ref.replace(/\.json$/, "")
                            navigate(`/analysis/${file}`)
                          }}
                        >
                          Jump to Analysis
                        </Button>
                      )}
                      <button
                        onClick={() => {
                          setSelectedRebalanceIndex(null)
                          // Remove rebalance query param from URL
                          const newSearchParams = new URLSearchParams(searchParams)
                          newSearchParams.delete("rebalance")
                          setSearchParams(newSearchParams)
                        }}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Balance</p>
                      <p className="text-lg font-semibold">{formatCurrency(selectedRebalance.balance)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Profit</p>
                      <p className={`text-lg font-semibold ${selectedRebalance.profit >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {formatCurrency(selectedRebalance.profit)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Profit %</p>
                      <p className={`text-lg font-semibold ${selectedRebalance.profit_pct >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {formatPercent(selectedRebalance.profit_pct * 100)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Investments</p>
                      <p className="text-lg font-semibold">{selectedRebalance.investments.length}</p>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Position</TableHead>
                          <TableHead>Buy Price</TableHead>
                          <TableHead>Buy Date</TableHead>
                          <TableHead>Sell Price</TableHead>
                          <TableHead>Sell Date</TableHead>
                          <TableHead>Profit %</TableHead>
                          <TableHead>Profit</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedRebalance.investments.map((investment, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-medium">{investment.symbol}</TableCell>
                            <TableCell>{investment.position.toFixed(4)}</TableCell>
                            <TableCell>{formatCurrency(investment.buy_price)}</TableCell>
                            <TableCell>{formatDate(investment.buy_date)}</TableCell>
                            <TableCell>{formatCurrency(investment.sell_price)}</TableCell>
                            <TableCell>{formatDate(investment.sell_date)}</TableCell>
                            <TableCell
                              className={
                                investment.profit_pct >= 0 ? "text-green-600" : "text-red-600"
                              }
                            >
                              {formatPercent(investment.profit_pct)}
                            </TableCell>
                            <TableCell
                              className={
                                investment.profit >= 0 ? "text-green-600" : "text-red-600"
                              }
                            >
                              {formatCurrency(investment.profit)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {/* Investments Table */}
              <div className="rounded-lg border bg-card p-6">
                <h2 className="mb-4 text-2xl font-semibold">
                  Investments ({allInvestments.length})
                </h2>
                <Tabs value={tableView} onValueChange={(v) => setTableView(v as "investment" | "rebalance")}>
                  <TabsList>
                    <TabsTrigger value="investment">By Investment</TabsTrigger>
                    <TabsTrigger value="rebalance">By Rebalance</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="investment">
                    <div className="overflow-x-auto mt-4">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Symbol</TableHead>
                            <TableHead>Position</TableHead>
                            <TableHead>Buy Price</TableHead>
                            <TableHead 
                              className="cursor-pointer select-none hover:bg-muted/50"
                              onClick={() => handleSort("buy_date")}
                            >
                              <div className="flex items-center gap-1">
                                Buy Date
                                {sortConfig.column === "buy_date" && (
                                  <span className="text-primary">
                                    {sortConfig.direction === "asc" ? (
                                      <ArrowUp className="h-3 w-3" />
                                    ) : (
                                      <ArrowDown className="h-3 w-3" />
                                    )}
                                  </span>
                                )}
                              </div>
                            </TableHead>
                            <TableHead>Sell Price</TableHead>
                            <TableHead>Sell Date</TableHead>
                            <TableHead 
                              className="cursor-pointer select-none hover:bg-muted/50"
                              onClick={() => handleSort("profit_pct")}
                            >
                              <div className="flex items-center gap-1">
                                Profit %
                                {sortConfig.column === "profit_pct" && (
                                  <span className="text-primary">
                                    {sortConfig.direction === "asc" ? (
                                      <ArrowUp className="h-3 w-3" />
                                    ) : (
                                      <ArrowDown className="h-3 w-3" />
                                    )}
                                  </span>
                                )}
                              </div>
                            </TableHead>
                            <TableHead 
                              className="cursor-pointer select-none hover:bg-muted/50"
                              onClick={() => handleSort("profit")}
                            >
                              <div className="flex items-center gap-1">
                                Profit
                                {sortConfig.column === "profit" && (
                                  <span className="text-primary">
                                    {sortConfig.direction === "asc" ? (
                                      <ArrowUp className="h-3 w-3" />
                                    ) : (
                                      <ArrowDown className="h-3 w-3" />
                                    )}
                                  </span>
                                )}
                              </div>
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {sortedInvestments.map((investment, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="font-medium">{investment.symbol}</TableCell>
                              <TableCell>{investment.position.toFixed(4)}</TableCell>
                              <TableCell>{formatCurrency(investment.buy_price)}</TableCell>
                              <TableCell>{formatDate(investment.buy_date)}</TableCell>
                              <TableCell>{formatCurrency(investment.sell_price)}</TableCell>
                              <TableCell>{formatDate(investment.sell_date)}</TableCell>
                              <TableCell
                                className={
                                  investment.profit_pct >= 0 ? "text-green-600" : "text-red-600"
                                }
                              >
                                {formatPercent(investment.profit_pct)}
                              </TableCell>
                              <TableCell
                                className={
                                  investment.profit >= 0 ? "text-green-600" : "text-red-600"
                                }
                              >
                                {formatCurrency(investment.profit)}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>

                  <TabsContent value="rebalance">
                    <div className="mt-4 space-y-6">
                      {simulationData?.rebalance_history.map((rebalance, rebalanceIdx) => (
                        <div key={rebalanceIdx} className="border rounded-lg p-4">
                          <div className="mb-4 pb-3 border-b">
                            <div className="flex flex-wrap items-center gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">Date: </span>
                                <span className="font-medium">{formatDate(rebalance.date)}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Balance: </span>
                                <span className="font-medium">{formatCurrency(rebalance.balance)}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Profit: </span>
                                <span className={`font-medium ${rebalance.profit >= 0 ? "text-green-600" : "text-red-600"}`}>
                                  {formatCurrency(rebalance.profit)} ({formatPercent(rebalance.profit_pct * 100)})
                                </span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Investments: </span>
                                <span className="font-medium">{rebalance.investments.length}</span>
                              </div>
                            </div>
                          </div>
                          <div className="overflow-x-auto">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Symbol</TableHead>
                                  <TableHead>Position</TableHead>
                                  <TableHead>Buy Price</TableHead>
                                  <TableHead>Buy Date</TableHead>
                                  <TableHead>Sell Price</TableHead>
                                  <TableHead>Sell Date</TableHead>
                                  <TableHead>Profit %</TableHead>
                                  <TableHead>Profit</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {rebalance.investments.map((investment, invIdx) => (
                                  <TableRow key={invIdx}>
                                    <TableCell className="font-medium">{investment.symbol}</TableCell>
                                    <TableCell>{investment.position.toFixed(4)}</TableCell>
                                    <TableCell>{formatCurrency(investment.buy_price)}</TableCell>
                                    <TableCell>{formatDate(investment.buy_date)}</TableCell>
                                    <TableCell>{formatCurrency(investment.sell_price)}</TableCell>
                                    <TableCell>{formatDate(investment.sell_date)}</TableCell>
                                    <TableCell
                                      className={
                                        investment.profit_pct >= 0 ? "text-green-600" : "text-red-600"
                                      }
                                    >
                                      {formatPercent(investment.profit_pct)}
                                    </TableCell>
                                    <TableCell
                                      className={
                                        investment.profit >= 0 ? "text-green-600" : "text-red-600"
                                      }
                                    >
                                      {formatCurrency(investment.profit)}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        </div>
                      ))}
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            </>
          ) : null}
        </main>
    </div>
  )
}
