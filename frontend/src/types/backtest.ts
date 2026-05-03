export interface BacktestInvestment {
  symbol: string
  position: number
  buy_price: number
  buy_date: string
  sell_price: number
  sell_date: string
  profit_pct: number
  profit: number
  stop_loss_price?: number | null
}

export interface BacktestRebalance {
  date: string
  balance: number
  investments: BacktestInvestment[]
  profit_pct: number
  profit: number
  baseline_profit_pct?: number
  baseline_profit?: number
  baseline_balance?: number
}

export interface StopLossConfig {
  expression: string
}

export interface BacktestConfig {
  max_stocks: number
  rebalance_interval_weeks: number
  date_start: string
  date_end: string
  rule: string
  sort_expr?: string
  index: string
  involved_keys?: string[]
  stop_loss?: StopLossConfig | null
  sell_timing?: "friday_close" | "monday_open"
  slippage_pct?: number
}

export interface BacktestScores {
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  max_drawdown_pct: number
  max_drawdown_duration_weeks: number
  win_rate: number
  avg_win_pct: number
  avg_loss_pct: number
  total_rebalances: number
}

export interface Backtest {
  id?: number
  initial_balance: number
  final_balance: number
  date_start: string
  date_end: string
  backtest_rebalance: BacktestRebalance[]
  profit_pct: number
  profit: number
  baseline_index?: string
  baseline_profit_pct?: number
  baseline_profit?: number
  baseline_balance?: number
  rule_ref?: string | null
  backtest_config?: BacktestConfig
  scores?: BacktestScores | null
}

export interface BacktestSummary {
  id: string
  strategy_id?: string | null
  date_start: string
  date_end: string
  profit_pct: number
  profit: number
  baseline_profit_pct: number
  index: string
  max_stocks?: number
  rebalance_interval_weeks?: number
  win_rate?: number | null
  max_drawdown_pct?: number | null
  created_at: string
}

export interface CreatedBacktest {
  backtest_id: string
}
