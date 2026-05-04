// Stock indicators - flat structure matching backend API
export interface StockIndicators {
  symbol: string;
  date: string;
  total_weeks: number;
  // Linear regression slope (% per week)
  slope_pct_4w: number;
  slope_pct_13w: number;
  slope_pct_26w: number;
  slope_pct_52w: number;
  // Linear regression R²
  r_squared_4w: number;
  r_squared_13w: number;
  r_squared_26w: number;
  r_squared_52w: number;
  // Log regression slope and R²
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
  // Weekly return std-dev
  return_std_52w: number;
  downside_std_52w: number;
  // Max drawdown per window
  max_drawdown_pct_4w: number;
  max_drawdown_pct_13w: number;
  max_drawdown_pct_26w: number;
  max_drawdown_pct_52w: number;
  // Fraction of up-weeks per window
  pct_weeks_positive_4w: number;
  pct_weeks_positive_13w: number;
  pct_weeks_positive_26w: number;
  pct_weeks_positive_52w: number;
  // Momentum shape
  acceleration_pct_4w: number;
  acceleration_pct_13w: number;
  acceleration_pct_26w: number;
  acceleration_pct_52w: number;
  from_high_pct_4w: number;
  // Moving average structure (price vs SMA, %)
  price_vs_ma20_pct?: number;
  price_vs_ma50_pct?: number;
  price_vs_ma100_pct?: number;
  price_vs_ma200_pct?: number;
  ma50_vs_ma200_pct?: number;
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
