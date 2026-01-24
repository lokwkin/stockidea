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
  baseline_profit_pct?: number
  baseline_profit?: number
  baseline_balance?: number
}

export interface SimulationConfig {
  max_stocks: number
  rebalance_interval_weeks: number
  date_start: string
  date_end: string
  rule: string
  index: string
}

export interface Simulation {
  id?: number
  initial_balance: number
  final_balance: number
  date_start: string
  date_end: string
  rebalance_history: RebalanceHistory[]
  profit_pct: number
  profit: number
  baseline_index?: string
  baseline_profit_pct?: number
  baseline_profit?: number
  baseline_balance?: number
  rule_ref?: string | null
  simulation_config?: SimulationConfig
}

export interface SimulationSummary {
  id: number
  date_start: string
  date_end: string
  profit_pct: number
  profit: number
  baseline_profit_pct: number
  created_at: string
}
