/**
 * Unified column display name mapping
 * Maps column keys to their display names for use across all tables
 */

export const COLUMN_NAMES: Record<string, string> = {
  // Stock Analysis columns
  symbol: "Symbol",
  total_weeks: "Weeks",
  above_1w: "> 1W Ago",
  above_2w: "> 2W Ago",
  above_4w: "> 4W Ago",
  biggest_weekly_jump_pct: "Best Week",
  biggest_weekly_drop_pct: "Worst Week",
  biggest_biweekly_jump_pct: "Best 2-Wk",
  biggest_biweekly_drop_pct: "Worst 2-Wk",
  biggest_monthly_jump_pct: "Best Mo",
  biggest_monthly_drop_pct: "Worst Mo",
  linear_slope_pct: "Linear Slope",
  linear_r_squared: "Linear R²",
  log_slope: "Log Slope",
  log_r_squared: "Log R²",
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
