import { useMemo, useCallback } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import type { Simulation } from "@/types/simulation"

interface ChartDataPoint {
  date: string
  dateRaw: string
  balance: number
  baselineBalance?: number
  investments: any[]
  rebalanceIndex?: number
}

interface BalanceChartProps {
  simulationData: Simulation
  selectedRebalanceIndex: number | null
  onRebalanceSelect: (index: number | null) => void
  formatDate: (dateStr: string) => string
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

function CustomTooltip(props: any) {
  const { active, payload, label } = props

  if (!active || !payload || !payload.length) {
    return null
  }

  const data = payload[0].payload as ChartDataPoint
  const investments = data.investments || []

  // Find baseline value from payload
  const baselinePayload = payload.find((p: any) => p.dataKey === "baselineBalance")
  const baselineBalance = baselinePayload?.value

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  const formatPercent = (value: number): string => {
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
  }

  return (
    <div className="rounded-lg border bg-card p-3 shadow-lg">
      <p className="font-semibold mb-2 text-sm">{label}</p>
      <p className="text-sm mb-2">
        Portfolio Balance: <span className="font-medium">{formatCurrency(data.balance)}</span>
      </p>
      {baselineBalance !== undefined && (
        <p className="text-sm mb-2">
          Baseline: <span className="font-medium">{formatCurrency(baselineBalance)}</span>
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

export function BalanceChart({
  simulationData,
  selectedRebalanceIndex,
  onRebalanceSelect,
  formatDate,
}: BalanceChartProps) {
  const chartData = useMemo(() => {
    return simulationData.rebalance_history.map((rebalance, index) => {
      return {
        date: formatDate(rebalance.date),
        dateRaw: rebalance.date,
        balance: rebalance.balance,
        baselineBalance: rebalance.baseline_balance,
        investments: rebalance.investments,
        rebalanceIndex: index,
      }
    })
  }, [simulationData, formatDate])

  // Check if we have any valid baseline balance data
  const hasBaselineData = useMemo(() => {
    return chartData.some((point) => point.baselineBalance !== undefined && point.baselineBalance > 0)
  }, [chartData])

  // Custom dot component that handles clicks
  const CustomDot = useCallback(
    (props: any) => {
      const { cx, cy, payload } = props
      if (cx == null || cy == null) return null

      const handleClick = (e: any) => {
        e.stopPropagation()
        e.preventDefault()
        const index = payload?.rebalanceIndex
        if (index !== undefined && index !== null) {
          const newIndex = selectedRebalanceIndex === index ? null : index
          onRebalanceSelect(newIndex)
        }
      }

      const handleMouseDown = (e: any) => {
        e.stopPropagation()
        handleClick(e)
      }

      return (
        <g onClick={handleClick} onMouseDown={handleMouseDown} style={{ cursor: "pointer" }}>
          {/* Larger invisible circle for easier clicking */}
          <circle
            cx={cx}
            cy={cy}
            r={10}
            fill="transparent"
            stroke="transparent"
            strokeWidth={0}
            style={{ pointerEvents: "all" }}
          />
          {/* Visible dot */}
          <circle
            cx={cx}
            cy={cy}
            r={4}
            fill="hsl(var(--primary))"
            style={{ pointerEvents: "none" }}
          />
        </g>
      )
    },
    [selectedRebalanceIndex, onRebalanceSelect]
  )

  const handleChartClick = useCallback(
    (data: any) => {
      if (data && data.activePayload && data.activePayload.length > 0) {
        const payload = data.activePayload[0].payload
        const index = payload.rebalanceIndex
        if (index !== undefined && index !== null) {
          const newIndex = selectedRebalanceIndex === index ? null : index
          onRebalanceSelect(newIndex)
        }
      }
    },
    [selectedRebalanceIndex, onRebalanceSelect]
  )

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="mb-4 text-2xl font-semibold">Balance History</h2>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} onClick={handleChartClick} style={{ cursor: "default" }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} style={{ fontSize: 12 }} />
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
                  const newIndex = selectedRebalanceIndex === index ? null : index
                  onRebalanceSelect(newIndex)
                }
              },
            }}
            name="Portfolio Balance"
          />
          {hasBaselineData && (
            <Line
              type="monotone"
              dataKey="baselineBalance"
              stroke="#8884d8"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name={simulationData.baseline_index || "Baseline"}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-muted-foreground text-center">
        Click on a data point to view rebalance details
      </p>
    </div>
  )
}
