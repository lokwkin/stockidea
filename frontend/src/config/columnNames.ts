/**
 * Unified column display name mapping
 * Maps column keys to their display names for use across all tables
 */

export const COLUMN_NAMES: Record<string, string> = {
  // Stock Analysis columns
  symbol: "Symbol",
  total_weeks: "Weeks",
  // Slope
  slope_pct_13w: "Slope 13W",
  slope_pct_26w: "Slope 26W",
  slope_pct_52w: "Slope 52W",
  // R²
  r_squared_4w: "R² 4W",
  r_squared_13w: "R² 13W",
  r_squared_26w: "R² 26W",
  r_squared_52w: "R² 52W",
  // Log regression
  log_slope_13w: "Log Slope 13W",
  log_r_squared_13w: "Log R² 13W",
  log_slope_26w: "Log Slope 26W",
  log_r_squared_26w: "Log R² 26W",
  log_slope_52w: "Log Slope 52W",
  log_r_squared_52w: "Log R² 52W",
  // Change
  change_pct_1w: "1W",
  change_pct_2w: "2W",
  change_pct_4w: "4W",
  change_pct_13w: "13W",
  change_pct_26w: "26W",
  change_pct_52w: "52W",
  // Max swing
  max_jump_pct_1w: "Max 1W Jump",
  max_drop_pct_1w: "Max 1W Drop",
  max_jump_pct_2w: "Max 2W Jump",
  max_drop_pct_2w: "Max 2W Drop",
  max_jump_pct_4w: "Max 4W Jump",
  max_drop_pct_4w: "Max 4W Drop",
  // Volatility (statistical)
  return_std_52w: "Vol (Std)",
  downside_std_52w: "Downside Vol",
  // Drawdown
  max_drawdown_pct_4w: "Drawdown 4W",
  max_drawdown_pct_13w: "Drawdown 13W",
  max_drawdown_pct_26w: "Drawdown 26W",
  max_drawdown_pct_52w: "Max DD",
  // % up-weeks
  pct_weeks_positive_4w: "% Wks + 4W",
  pct_weeks_positive_13w: "% Wks + 13W",
  pct_weeks_positive_26w: "% Wks + 26W",
  pct_weeks_positive_52w: "% Wks +",
  // Momentum shape
  acceleration_pct_13w: "Accel 13W",
  from_high_pct_4w: "From 4W High",
  // Moving average structure
  price_vs_ma20_pct: "Px vs MA20",
  price_vs_ma50_pct: "Px vs MA50",
  price_vs_ma100_pct: "Px vs MA100",
  price_vs_ma200_pct: "Px vs MA200",
  ma50_vs_ma200_pct: "MA50/MA200",

  // BacktestInvestment columns
  position: "Position",
  buy_price: "Buy Price",
  buy_date: "Buy Date",
  sell_price: "Sell Price",
  sell_date: "Sell Date",
  stop_loss_price: "Stop Loss",
  profit_pct: "Profit %",
  profit: "Profit",
}

/**
 * Get display name for a column key
 * Falls back to the key itself if not found
 */
export function getColumnDisplayName(key: string): string {
  return COLUMN_NAMES[key] || key
}
