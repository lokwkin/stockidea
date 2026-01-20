import { useEffect, useState, useMemo, useCallback } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { ArrowUp, ArrowDown } from "lucide-react"
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

interface ChartDataPoint {
  date: string
  dateRaw: string
  balance: number
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

  return (
    <div className="rounded-lg border bg-card p-3 shadow-lg">
      <p className="font-semibold mb-2 text-sm">{label}</p>
      <p className="text-sm mb-2">
        Balance: <span className="font-medium">{formatCurrency(data.balance)}</span>
      </p>
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

interface SimulationViewProps {
  onNavigateToAnalysis?: (file: string) => void
}

export function SimulationView({ onNavigateToAnalysis }: SimulationViewProps = {}) {
  const [simulations, setSimulations] = useState<string[]>([])
  const [selectedSimulation, setSelectedSimulation] = useState<string>("")
  const [simulationData, setSimulationData] = useState<Simulation | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tableView, setTableView] = useState<"investment" | "rebalance">("investment")
  const [selectedRebalanceIndex, setSelectedRebalanceIndex] = useState<number | null>(null)
  const [sortConfig, setSortConfig] = useState<{ column: SortColumn; direction: SortDirection }>({
    column: null,
    direction: null,
  })

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
        setSelectedSimulation(files[0])
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
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

  const handleSort = useCallback((column: SortColumn) => {
    setSortConfig((prev) => {
      if (prev.column === column) {
        if (prev.direction === "asc") return { column, direction: "desc" }
        if (prev.direction === "desc") return { column: null, direction: null }
      }
      return { column, direction: "asc" }
    })
  }, [])

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
  }, [allInvestments, sortConfig])

  const handleChartClick = useCallback((data: any) => {
    if (data && data.activePayload && data.activePayload.length > 0) {
      const payload = data.activePayload[0].payload
      const index = payload.rebalanceIndex
      if (index !== undefined && index !== null) {
        setSelectedRebalanceIndex((prev) => prev === index ? null : index)
      }
    }
  }, [])

  // Custom dot component that handles clicks
  const CustomDot = useCallback((props: any) => {
    const { cx, cy, payload } = props
    if (cx == null || cy == null) return null
    
    const handleClick = (e: any) => {
      e.stopPropagation()
      e.preventDefault()
      const index = payload?.rebalanceIndex
      if (index !== undefined && index !== null) {
        setSelectedRebalanceIndex((prev) => prev === index ? null : index)
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
  }, [setSelectedRebalanceIndex])

  const chartData = useMemo(() => {
    if (!simulationData) return []
    return simulationData.rebalance_history.map((rebalance, index) => {
      return {
        date: formatDate(rebalance.date),
        dateRaw: rebalance.date,
        balance: rebalance.balance,
        investments: rebalance.investments,
        rebalanceIndex: index,
      }
    })
  }, [simulationData])

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
            <Select value={selectedSimulation} onValueChange={setSelectedSimulation}>
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
                          if (index !== undefined && index !== null) {
                            setSelectedRebalanceIndex((prev) => prev === index ? null : index)
                          }
                        }
                      }}
                      name="Balance"
                    />
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
                      {selectedRebalance.analysis_ref && onNavigateToAnalysis && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            // Remove .json extension if present, as API expects filename without extension
                            const file = selectedRebalance.analysis_ref.replace(/\.json$/, "")
                            onNavigateToAnalysis(file)
                          }}
                        >
                          Jump to Analysis
                        </Button>
                      )}
                      <button
                        onClick={() => setSelectedRebalanceIndex(null)}
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
