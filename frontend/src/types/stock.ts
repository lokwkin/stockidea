// Stock metrics - flat structure matching backend API
export interface StockMetrics {
  symbol: string;
  date: string;
  total_weeks: number;
  // Trend metrics (regression-based)
  linear_slope_pct: number;
  linear_r_squared: number;
  log_slope: number;
  log_r_squared: number;
  // Return metrics (point-to-point changes)
  change_1w_pct: number;
  change_2w_pct: number;
  change_1m_pct: number;
  change_3m_pct: number;
  change_6m_pct: number;
  change_1y_pct: number;
  // Volatility metrics (max swings)
  max_jump_1w_pct: number;
  max_drop_1w_pct: number;
  max_jump_2w_pct: number;
  max_drop_2w_pct: number;
  max_jump_4w_pct: number;
  max_drop_4w_pct: number;
}

// API response type
export interface MetricsDataAPI {
  date: string;
  data: StockMetrics[];
}

export type SortDirection = "asc" | "desc" | null;

export interface SortConfig {
  column: keyof StockMetrics | null;
  direction: SortDirection;
}

export interface Filter {
  id: number;
  column: keyof StockMetrics;
  operator: ">" | "<" | ">=" | "<=" | "=" | "contains";
  value: string | number;
  displayName: string;
}

export type ColumnType =
  | "string"
  | "number"
  | "percent"
  | "r_squared"
  | "pct_bar";

export interface ColumnConfig {
  key: keyof StockMetrics;
  displayName: string;
  filterName: string;
  type: ColumnType;
  decimals?: number;
}
