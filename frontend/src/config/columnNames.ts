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
  change_4w_pct: "4W",
  change_13w_pct: "13W",
  change_26w_pct: "26W",
  change_1y_pct: "1Y",
  // Volatility (statistical)
  weekly_return_std: "Vol (Std)",
  downside_std: "Downside Vol",
  // Stability
  max_drawdown_pct: "Max DD",
  pct_weeks_positive: "% Wks +",
  slope_13w_pct: "Slope 13W",
  r_squared_13w: "R² 13W",
  r_squared_4w: "R² 4W",
  slope_26w_pct: "Slope 26W",
  r_squared_26w: "R² 26W",
  // Momentum shape
  acceleration_13w: "Accel 13W",
  pct_from_4w_high: "From 4W High",
  
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
