// Stock metrics - flat structure matching backend API
export interface StockMetrics {
  symbol: string;
  date: string;
  total_weeks: number;
  // Slope
  slope_pct_13w: number;
  slope_pct_26w: number;
  slope_pct_52w: number;
  // R²
  r_squared_13w: number;
  r_squared_26w: number;
  r_squared_52w: number;
  // Log trend
  log_slope_13w: number;
  log_r_squared_13w: number;
  log_slope_26w: number;
  log_r_squared_26w: number;
  log_slope_52w: number;
  log_r_squared_52w: number;
  // Point-to-point change
  change_pct_1w: number;
  change_pct_2w: number;
  change_pct_4w: number;
  change_pct_13w: number;
  change_pct_26w: number;
  change_pct_52w: number;
  // Max single-period swing
  max_jump_pct_1w: number;
  max_drop_pct_1w: number;
  max_jump_pct_2w: number;
  max_drop_pct_2w: number;
  max_jump_pct_4w: number;
  max_drop_pct_4w: number;
  // Max drawdown
  max_drawdown_pct_4w: number;
  max_drawdown_pct_13w: number;
  max_drawdown_pct_26w: number;
  max_drawdown_pct_52w: number;
  // Fraction of up-weeks
  pct_weeks_positive_4w: number;
  pct_weeks_positive_13w: number;
  pct_weeks_positive_26w: number;
  pct_weeks_positive_52w: number;
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
