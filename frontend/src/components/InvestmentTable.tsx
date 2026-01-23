import { useMemo, useCallback, useState } from "react"
import { ArrowUp, ArrowDown } from "lucide-react"
import type { Investment } from "@/types/simulation"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

type SortColumn = "buy_date" | "profit" | "profit_pct" | null
type SortDirection = "asc" | "desc" | null

interface InvestmentTableProps {
  investments: Investment[]
  formatDate: (dateStr: string) => string
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

export function InvestmentTable({
  investments,
  formatDate,
  formatCurrency,
  formatPercent,
}: InvestmentTableProps) {
  const [sortConfig, setSortConfig] = useState<{ column: SortColumn; direction: SortDirection }>({
    column: null,
    direction: null,
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

  const sortedInvestments = useMemo(() => {
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
  )
}
