/**
 * Unified column display name mapping
 * Maps column keys to their display names for use across all tables
 */

export const COLUMN_NAMES: Record<string, string> = {
  // Stock Analysis columns
  symbol: "Symbol",
  total_weeks: "Weeks",
  max_jump_1w_pct: "Max 1W Jump",
  max_drop_1w_pct: "Max 1W Drop",
  max_jump_2w_pct: "Max 2W Jump",
  max_drop_2w_pct: "Max 2W Drop",
  max_jump_4w_pct: "Max 4W Jump",
  max_drop_4w_pct: "Max 4W Drop",
  linear_slope_pct: "Linear Slope",
  linear_r_squared: "Linear R²",
  log_slope: "Log Slope",
  log_r_squared: "Log R²",
  change_1w_pct: "1W",
  change_2w_pct: "2W",
  change_1m_pct: "1M",
  change_3m_pct: "3M",
  change_6m_pct: "6M",
  change_1y_pct: "1Y",
  
  // Investment columns
  position: "Position",
  buy_price: "Buy Price",
  buy_date: "Buy Date",
  sell_price: "Sell Price",
  sell_date: "Sell Date",
  profit_pct: "Profit %",
  profit: "Profit",
  
  // Analysis Panel specific (can use same as above)
  // linear_slope_pct already defined above
  // linear_r_squared already defined above
}

/**
 * Get display name for a column key
 * Falls back to the key itself if not found
 */
export function getColumnDisplayName(key: string): string {
  return COLUMN_NAMES[key] || key
}
