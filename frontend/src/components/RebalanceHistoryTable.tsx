import type { RebalanceHistory } from "@/types/simulation"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface RebalanceHistoryTableProps {
  rebalanceHistory: RebalanceHistory[]
  formatDate: (dateStr: string) => string
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

export function RebalanceHistoryTable({
  rebalanceHistory,
  formatDate,
  formatCurrency,
  formatPercent,
}: RebalanceHistoryTableProps) {
  return (
    <div className="mt-4 space-y-6">
      {rebalanceHistory.map((rebalance, rebalanceIdx) => (
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
  )
}
