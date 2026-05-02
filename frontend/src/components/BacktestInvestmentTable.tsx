import { useMemo, useCallback, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowUp, ArrowDown } from "lucide-react"
import type { BacktestInvestment } from "@/types/backtest"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getColumnDisplayName } from "@/config/columnNames"

type SortColumn = "buy_date" | "profit" | "profit_pct" | null
type SortDirection = "asc" | "desc" | null

interface BacktestInvestmentTableProps {
  investments: BacktestInvestment[]
  formatDate: (dateStr: string) => string
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

export function BacktestInvestmentTable({
  investments,
  formatDate,
  formatCurrency,
  formatPercent,
}: BacktestInvestmentTableProps) {
  const [sortConfig, setSortConfig] = useState<{ column: SortColumn; direction: SortDirection }>({
    column: "buy_date",
    direction: "desc",
  })

  const handleSort = useCallback((column: SortColumn) => {
    setSortConfig((prev) => {
      if (prev.column === column) {
        if (prev.direction === "asc") return { column, direction: "desc" }
        if (prev.direction === "desc") return { column: null, direction: null }
      }
      return { column, direction: "asc" }
    })
  }, [])

  const sortedBacktestInvestments = useMemo(() => {
    const sorted = [...investments]

    if (!sortConfig.column || !sortConfig.direction) {
      return sorted
    }

    return sorted.sort((a, b) => {
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
  }, [investments, sortConfig])

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{getColumnDisplayName("symbol")}</TableHead>
            <TableHead>{getColumnDisplayName("position")}</TableHead>
            <TableHead>{getColumnDisplayName("buy_price")}</TableHead>
            <TableHead
              className="cursor-pointer select-none hover:bg-muted/50"
              onClick={() => handleSort("buy_date")}
            >
              <div className="flex items-center gap-1">
                {getColumnDisplayName("buy_date")}
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
            <TableHead>{getColumnDisplayName("sell_price")}</TableHead>
            <TableHead>{getColumnDisplayName("sell_date")}</TableHead>
            <TableHead>{getColumnDisplayName("stop_loss_price")}</TableHead>
            <TableHead
              className="cursor-pointer select-none hover:bg-muted/50"
              onClick={() => handleSort("profit_pct")}
            >
              <div className="flex items-center gap-1">
                {getColumnDisplayName("profit_pct")}
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
                {getColumnDisplayName("profit")}
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
          {sortedBacktestInvestments.map((investment, idx) => (
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
  )
}
