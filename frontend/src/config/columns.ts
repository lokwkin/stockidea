import type { ColumnConfig } from "@/types/stock"
import { getColumnDisplayName } from "./columnNames"

export const COLUMNS: ColumnConfig[] = [
  {
    key: "symbol",
    displayName: getColumnDisplayName("symbol"),
    filterName: "Symbol",
    type: "string",
  },
  {
    key: "total_weeks",
    displayName: getColumnDisplayName("total_weeks"),
    filterName: "Weeks",
    type: "number",
    decimals: 0,
  },
  // Change
  {
    key: "change_pct_1w",
    displayName: getColumnDisplayName("change_pct_1w"),
    filterName: "1W Change",
    type: "percent",
    decimals: 2,
  },
  {
    key: "change_pct_2w",
    displayName: getColumnDisplayName("change_pct_2w"),
    filterName: "2W Change",
    type: "percent",
    decimals: 2,
  },
  {
    key: "change_pct_4w",
    displayName: getColumnDisplayName("change_pct_4w"),
    filterName: "4W Change",
    type: "percent",
    decimals: 2,
  },
  {
    key: "change_pct_13w",
    displayName: getColumnDisplayName("change_pct_13w"),
    filterName: "13W Change",
    type: "percent",
    decimals: 2,
  },
  {
    key: "change_pct_26w",
    displayName: getColumnDisplayName("change_pct_26w"),
    filterName: "26W Change",
    type: "percent",
    decimals: 2,
  },
  {
    key: "change_pct_52w",
    displayName: getColumnDisplayName("change_pct_52w"),
    filterName: "52W Change",
    type: "percent",
    decimals: 2,
  },
  // Slope
  {
    key: "slope_pct_13w",
    displayName: getColumnDisplayName("slope_pct_13w"),
    filterName: "Slope 13W",
    type: "number",
    decimals: 2,
  },
  {
    key: "slope_pct_26w",
    displayName: getColumnDisplayName("slope_pct_26w"),
    filterName: "Slope 26W",
    type: "number",
    decimals: 2,
  },
  {
    key: "slope_pct_52w",
    displayName: getColumnDisplayName("slope_pct_52w"),
    filterName: "Slope 52W",
    type: "number",
    decimals: 2,
  },
  // R²
  {
    key: "r_squared_13w",
    displayName: getColumnDisplayName("r_squared_13w"),
    filterName: "R² 13W",
    type: "r_squared",
    decimals: 3,
  },
  {
    key: "r_squared_26w",
    displayName: getColumnDisplayName("r_squared_26w"),
    filterName: "R² 26W",
    type: "r_squared",
    decimals: 3,
  },
  {
    key: "r_squared_52w",
    displayName: getColumnDisplayName("r_squared_52w"),
    filterName: "R² 52W",
    type: "r_squared",
    decimals: 3,
  },
  // Log slope
  {
    key: "log_slope_52w",
    displayName: getColumnDisplayName("log_slope_52w"),
    filterName: "Log Slope 52W",
    type: "number",
    decimals: 4,
  },
  // Log R²
  {
    key: "log_r_squared_52w",
    displayName: getColumnDisplayName("log_r_squared_52w"),
    filterName: "Log R² 52W",
    type: "r_squared",
    decimals: 3,
  },
  // Max swing
  {
    key: "max_jump_pct_1w",
    displayName: getColumnDisplayName("max_jump_pct_1w"),
    filterName: "Max 1W Jump",
    type: "percent",
    decimals: 2,
  },
  {
    key: "max_drop_pct_1w",
    displayName: getColumnDisplayName("max_drop_pct_1w"),
    filterName: "Max 1W Drop",
    type: "percent",
    decimals: 2,
  },
  {
    key: "max_jump_pct_2w",
    displayName: getColumnDisplayName("max_jump_pct_2w"),
    filterName: "Max 2W Jump",
    type: "percent",
    decimals: 2,
  },
  {
    key: "max_drop_pct_2w",
    displayName: getColumnDisplayName("max_drop_pct_2w"),
    filterName: "Max 2W Drop",
    type: "percent",
    decimals: 2,
  },
  {
    key: "max_jump_pct_4w",
    displayName: getColumnDisplayName("max_jump_pct_4w"),
    filterName: "Max 4W Jump",
    type: "percent",
    decimals: 2,
  },
  {
    key: "max_drop_pct_4w",
    displayName: getColumnDisplayName("max_drop_pct_4w"),
    filterName: "Max 4W Drop",
    type: "percent",
    decimals: 2,
  },
  // Max drawdown
  {
    key: "max_drawdown_pct_13w",
    displayName: getColumnDisplayName("max_drawdown_pct_13w"),
    filterName: "Drawdown 13W",
    type: "percent",
    decimals: 2,
  },
  {
    key: "max_drawdown_pct_26w",
    displayName: getColumnDisplayName("max_drawdown_pct_26w"),
    filterName: "Drawdown 26W",
    type: "percent",
    decimals: 2,
  },
  {
    key: "max_drawdown_pct_52w",
    displayName: getColumnDisplayName("max_drawdown_pct_52w"),
    filterName: "Drawdown 52W",
    type: "percent",
    decimals: 2,
  },
  // % up-weeks
  {
    key: "pct_weeks_positive_52w",
    displayName: getColumnDisplayName("pct_weeks_positive_52w"),
    filterName: "Up Weeks 52W",
    type: "number",
    decimals: 2,
  },
]
