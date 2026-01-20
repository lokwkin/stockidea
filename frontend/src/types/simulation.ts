export interface Investment {
  symbol: string
  position: number
  buy_price: number
  buy_date: string
  sell_price: number
  sell_date: string
  profit_pct: number
  profit: number
}

export interface RebalanceHistory {
  date: string
  balance: number
  analysis_ref: string
  investments: Investment[]
  profit_pct: number
  profit: number
}

export interface Simulation {
  initial_balance: number
  date_start: string
  date_end: string
  rebalance_history: RebalanceHistory[]
  profit_pct: number
  profit: number
  rule_ref?: string | null
}
