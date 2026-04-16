import type { BacktestScores } from "./agent"

export type StrategyStatus = "idle" | "running" | "failed"

export interface StrategySummary {
  id: string
  name: string
  instruction: string
  model: string
  status: StrategyStatus
  created_at: string
  updated_at: string
}

export interface StrategyMessage {
  id: string
  role: "user" | "assistant"
  content_json: string
  created_at: string
  sequence: number
}

export interface StrategyBacktestSummary {
  id: string
  rule: string
  profit_pct: number
  baseline_profit_pct: number
  scores: BacktestScores | null
  created_at: string
}

export interface StrategyDetail {
  id: string
  name: string
  instruction: string
  model: string
  date_start: string
  date_end: string
  status: StrategyStatus
  created_at: string
  updated_at: string
  messages: StrategyMessage[]
  backtests: StrategyBacktestSummary[]
}

export interface StrategyCreateRequest {
  instruction: string
  model: string
  date_start?: string
  date_end?: string
}
