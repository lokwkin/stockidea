// Stock indicators - flat structure matching backend API
export interface StockIndicators {
  symbol: string;
  date: string;
  total_weeks: number;
  // Trend indicators (regression-based)
  linear_slope_pct: number;
  linear_r_squared: number;
  log_slope: number;
  log_r_squared: number;
  // Return indicators (point-to-point changes)
  change_1w_pct: number;
  change_2w_pct: number;
  change_4w_pct: number;
  change_13w_pct: number;
  change_26w_pct: number;
  change_1y_pct: number;
  // Volatility indicators (max swings)
  max_jump_1w_pct: number;
  max_drop_1w_pct: number;
  max_jump_2w_pct: number;
  max_drop_2w_pct: number;
  max_jump_4w_pct: number;
  max_drop_4w_pct: number;
  // Volatility indicators (statistical)
  weekly_return_std: number;
  downside_std: number;
  // Stability indicators
  max_drawdown_pct: number;
  pct_weeks_positive: number;
  slope_13w_pct: number;
  r_squared_13w: number;
  r_squared_4w: number;
  slope_26w_pct: number;
  r_squared_26w: number;
  // Momentum shape
  acceleration_13w: number;
  pct_from_4w_high: number;
}

// API response type
export interface IndicatorsDataAPI {
  date: string;
  data: StockIndicators[];
}

// FMP company profile (subset of fields we surface in UI)
export interface CompanyProfile {
  symbol?: string;
  companyName?: string;
  description?: string;
  industry?: string;
  sector?: string;
  country?: string;
  exchange?: string;
  exchangeShortName?: string;
  ceo?: string;
  website?: string;
  fullTimeEmployees?: string;
  mktCap?: number;
  beta?: number;
  ipoDate?: string;
  image?: string;
  isEtf?: boolean;
  isFund?: boolean;
  isAdr?: boolean;
}

export interface StockProfileResponse {
  symbol: string;
  profile: CompanyProfile | null;
  peers: string[];
}

export type SortDirection = "asc" | "desc" | null;

export interface SortConfig {
  column: keyof StockIndicators | null;
  direction: SortDirection;
}

export interface Filter {
  id: number;
  column: keyof StockIndicators;
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
  key: keyof StockIndicators;
  displayName: string;
  filterName: string;
  type: ColumnType;
  decimals?: number;
  group?: string;
}
