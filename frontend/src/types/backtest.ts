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
  investments: Investment[]
  profit_pct: number
  profit: number
  baseline_profit_pct?: number
  baseline_profit?: number
  baseline_balance?: number
}

export interface BacktestConfig {
  max_stocks: number
  rebalance_interval_weeks: number
  date_start: string
  date_end: string
  rule: string
  index: string
  involved_keys?: string[]
}

export interface Backtest {
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
  backtest_config?: BacktestConfig
}

export interface BacktestSummary {
  id: number
  date_start: string
  date_end: string
  profit_pct: number
  profit: number
  baseline_profit_pct: number
  created_at: string
}

export type JobStatus = "pending" | "running" | "completed" | "failed"

export interface BacktestJob {
  id: string
  status: JobStatus
  backtest_id: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface EnqueuedJob {
  job_id: string
  status: JobStatus
}
