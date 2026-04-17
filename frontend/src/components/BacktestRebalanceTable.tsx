import { useMemo } from "react"
import { Link } from "react-router-dom"
import type { BacktestRebalance } from "@/types/backtest"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getColumnDisplayName } from "@/config/columnNames"

interface BacktestRebalanceTableProps {
  rebalanceHistory: BacktestRebalance[]
  formatDate: (dateStr: string) => string
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

export function BacktestRebalanceTable({
  rebalanceHistory,
  formatDate,
  formatCurrency,
  formatPercent,
}: BacktestRebalanceTableProps) {
  const sortedRebalances = useMemo(
    () =>
      [...rebalanceHistory].sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
      ),
    [rebalanceHistory]
  )

  return (
    <div className="mt-4 space-y-6">
      {sortedRebalances.map((rebalance, rebalanceIdx) => (
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
                <span className={`font-medium ${rebalance.profit >= 0 ? "text-positive" : "text-negative"}`}>
                  {formatCurrency(rebalance.profit)} ({formatPercent(rebalance.profit_pct)})
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
                {rebalance.investments.map((investment, invIdx) => (
                  <TableRow key={invIdx}>
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
        </div>
      ))}
    </div>
  )
}
