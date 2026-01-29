import { useEffect, useState, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import type { RebalanceHistory } from "@/types/simulation"
import type { StockMetrics, MetricsDataAPI } from "@/types/stock"
import { StockTable } from "@/components/StockTable"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getColumnDisplayName } from "@/config/columnNames"

interface RebalanceDetailViewProps {
  rebalance: RebalanceHistory
  formatDate: (dateStr: string) => string
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
  onClose: () => void
  onOpenAnalysis?: (analysisDate: string) => void
}

export function RebalanceDetailView({
  rebalance,
  formatDate,
  formatCurrency,
  formatPercent,
  onClose,
  onOpenAnalysis,
}: RebalanceDetailViewProps) {
  const navigate = useNavigate()
  const [analysisData, setAnalysisData] = useState<{ date: string; data: StockMetrics[] } | null>(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)

  // Load metrics data when rebalance changes
  useEffect(() => {
    if (!rebalance.date) {
      setAnalysisData(null)
      return
    }

    let cancelled = false

    setLoadingAnalysis(true)
    setAnalysisData(null)

    // Use the rebalance date to query metrics
    const metricsDate = rebalance.date.split("T")[0] // Ensure we only use the date part

    fetch(`/api/metrics/${metricsDate}/`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load metrics data")
        return res.json()
      })
      .then((json: MetricsDataAPI) => {
        if (!cancelled) {
          setAnalysisData({ date: json.date, data: json.data })
          setLoadingAnalysis(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error("Failed to load metrics data:", err)
          setAnalysisData(null)
          setLoadingAnalysis(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [rebalance])

  // Filter analysis data to only show stocks in the rebalance investments
  const filteredAnalysisData = useMemo(() => {
    if (!analysisData) return null

    const investmentSymbols = new Set(rebalance.investments.map((inv) => inv.symbol))
    const filtered = analysisData.data.filter((stock) => investmentSymbols.has(stock.symbol))

    return {
      ...analysisData,
      data: filtered,
    }
  }, [analysisData, rebalance])

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Rebalance Details - {formatDate(rebalance.date)}</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const metricsDate = rebalance.date.split("T")[0] // Ensure we only use the date part
              if (onOpenAnalysis) {
                onOpenAnalysis(metricsDate)
              } else {
                navigate(`/analysis/${metricsDate}`)
              }
            }}
          >
            Open Trend Data
          </Button>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            ×
          </button>
        </div>
      </div>
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div>
          <p className="text-sm text-muted-foreground">Balance</p>
          <p className="text-lg font-semibold">{formatCurrency(rebalance.balance)}</p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Profit</p>
          <p className={`text-lg font-semibold ${rebalance.profit >= 0 ? "text-green-600" : "text-red-600"}`}>
            {formatCurrency(rebalance.profit)}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Profit %</p>
          <p className={`text-lg font-semibold ${rebalance.profit_pct >= 0 ? "text-green-600" : "text-red-600"}`}>
            {formatPercent(rebalance.profit_pct * 100)}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Investments</p>
          <p className="text-lg font-semibold">{rebalance.investments.length}</p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{getColumnDisplayName("symbol")}</TableHead>
              <TableHead>{getColumnDisplayName("position")}</TableHead>
              <TableHead>{getColumnDisplayName("buy_price")}</TableHead>
              <TableHead>{getColumnDisplayName("buy_date")}</TableHead>
              <TableHead>{getColumnDisplayName("sell_price")}</TableHead>
              <TableHead>{getColumnDisplayName("sell_date")}</TableHead>
              <TableHead>{getColumnDisplayName("profit_pct")}</TableHead>
              <TableHead>{getColumnDisplayName("profit")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rebalance.investments.map((investment, idx) => (
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

      {/* Trend Data Section */}
      <div className="mt-8">
        <h3 className="mb-4 text-xl font-semibold">Trend Data (Filtered by Selected Stocks)</h3>
        {loadingAnalysis ? (
          <div className="flex items-center justify-center py-8">
            <div className="flex flex-col items-center gap-4">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">Loading trend data...</p>
            </div>
          </div>
        ) : filteredAnalysisData ? (
          <StockTable data={filteredAnalysisData.data} />
        ) : (
          <div className="rounded-lg border border-muted bg-muted/30 p-4 text-center text-sm text-muted-foreground">
            Trend data not available for this date
          </div>
        )}
      </div>
    </div>
  )
}
