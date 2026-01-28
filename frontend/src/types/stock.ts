export interface StockAnalysis {
  symbol: string
  max_jump_1w_pct: number
  max_drop_1w_pct: number
  max_jump_2w_pct: number
  max_drop_2w_pct: number
  max_jump_4w_pct: number
  max_drop_4w_pct: number
  change_1y_pct: number
  change_6m_pct: number
  change_3m_pct: number
  change_1m_pct: number
  change_2w_pct: number
  change_1w_pct: number
  total_weeks: number
  linear_slope_pct: number
  linear_r_squared: number
  log_slope: number
  log_r_squared: number
}

export interface AnalysisData {
  analysis_date: string
  data: StockAnalysis[]
}

export type SortDirection = "asc" | "desc" | null

export interface SortConfig {
  column: keyof StockAnalysis | null
  direction: SortDirection
}

export interface Filter {
  id: number
  column: keyof StockAnalysis
  operator: ">" | "<" | ">=" | "<=" | "=" | "contains"
  value: string | number
  displayName: string
}

export type ColumnType = "string" | "number" | "percent" | "r_squared" | "pct_bar"

export interface ColumnConfig {
  key: keyof StockAnalysis
  displayName: string
  filterName: string
  type: ColumnType
  decimals?: number
}
