export interface StockAnalysis {
  symbol: string
  weeks_above_1_week_ago: number
  weeks_above_2_weeks_ago: number
  weeks_above_4_weeks_ago: number
  biggest_weekly_jump_pct: number
  biggest_weekly_drop_pct: number
  biggest_biweekly_jump_pct: number
  biggest_biweekly_drop_pct: number
  biggest_monthly_jump_pct: number
  biggest_monthly_drop_pct: number
  change_1y_pct: number
  change_6m_pct: number
  change_3m_pct: number
  change_1m_pct: number
  total_weeks: number
  // trend_slope_pct: number
  annualized_slope: number
  trend_r_squared: number
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
  key: keyof StockAnalysis | "above_1w" | "above_2w" | "above_4w"
  displayName: string
  filterName: string
  type: ColumnType
  decimals?: number
}
