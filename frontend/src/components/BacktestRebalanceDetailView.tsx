import { useEffect, useState, useMemo } from "react"
import { Link, useNavigate } from "react-router-dom"
import type { BacktestRebalance } from "@/types/backtest"
import type { StockIndicators, IndicatorsDataAPI } from "@/types/stock"
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

interface BacktestRebalanceDetailViewProps {
  rebalance: BacktestRebalance
  formatDate: (dateStr: string) => string
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
  onClose: () => void
  onOpenAnalysis?: (analysisDate: string) => void
}

export function BacktestRebalanceDetailView({
  rebalance,
  formatDate,
  formatCurrency,
  formatPercent,
  onClose,
  onOpenAnalysis,
}: BacktestRebalanceDetailViewProps) {
  const navigate = useNavigate()
  const [analysisData, setAnalysisData] = useState<{ date: string; data: StockIndicators[] } | null>(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)

  // Load indicator data when rebalance changes
  useEffect(() => {
    if (!rebalance.date) {
      setAnalysisData(null)
      return
    }

    let cancelled = false

    setLoadingAnalysis(true)
    setAnalysisData(null)

    // Use the rebalance date to query indicators
    const indicatorsDate = rebalance.date.split("T")[0] // Ensure we only use the date part

    fetch(`/api/indicators/${indicatorsDate}/`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load indicator data")
        return res.json()
      })
      .then((json: IndicatorsDataAPI) => {
        if (!cancelled) {
          setAnalysisData({ date: json.date, data: json.data })
          setLoadingAnalysis(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error("Failed to load indicator data:", err)
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
              const indicatorsDate = rebalance.date.split("T")[0] // Ensure we only use the date part
              if (onOpenAnalysis) {
                onOpenAnalysis(indicatorsDate)
              } else {
                navigate(`/analysis/${indicatorsDate}`)
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
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Balance</p>
          <p className="text-lg font-semibold">{formatCurrency(rebalance.balance)}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Profit</p>
          <p className={`text-lg font-semibold ${rebalance.profit >= 0 ? "text-positive" : "text-negative"}`}>
            {formatCurrency(rebalance.profit)}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Profit %</p>
          <p className={`text-lg font-semibold ${rebalance.profit_pct >= 0 ? "text-positive" : "text-negative"}`}>
            {formatPercent(rebalance.profit_pct)}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Investments</p>
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
              <TableHead>{getColumnDisplayName("stop_loss_price")}</TableHead>
              <TableHead>{getColumnDisplayName("profit_pct")}</TableHead>
              <TableHead>{getColumnDisplayName("profit")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rebalance.investments.map((investment, idx) => (
              <TableRow key={idx}>
                <TableCell className="font-medium">
                  <Link
                    to={`/chart/${investment.symbol}`}
                    className="text-primary hover:underline"
                  >
                    {investment.symbol}
                  </Link>
                </TableCell>
                <TableCell className="font-mono tabular-nums">{investment.position.toFixed(4)}</TableCell>
                <TableCell className="font-mono tabular-nums">{formatCurrency(investment.buy_price)}</TableCell>
                <TableCell>{formatDate(investment.buy_date)}</TableCell>
                <TableCell className="font-mono tabular-nums">{formatCurrency(investment.sell_price)}</TableCell>
                <TableCell>{formatDate(investment.sell_date)}</TableCell>
                <TableCell className="font-mono tabular-nums text-muted-foreground">
                  {investment.stop_loss_price != null ? formatCurrency(investment.stop_loss_price) : "—"}
                </TableCell>
                <TableCell
                  className={`font-mono tabular-nums ${
                    investment.profit_pct >= 0 ? "text-positive" : "text-negative"
                  }`}
                >
                  {formatPercent(investment.profit_pct)}
                </TableCell>
                <TableCell
                  className={`font-mono tabular-nums ${
                    investment.profit >= 0 ? "text-positive" : "text-negative"
                  }`}
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
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Loading trend data...</p>
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
