# Stockpick


### Start API
```
uv run python -m stockpick.api
```

### Analyze
```bash
Usage: python -m stockpick.cli analyze [OPTIONS]

  Analyze stock prices for a given date

Options:
  -d, --date TEXT                 Analysis date in YYYY-MM-DD format
  -i, --index [SP500|DOWJONES|NASDAQ]
                                  Stock index to analyze
  --help                          Show this message and exit.

# Example
uv run python -m stockpick.cli analyze -d 2026-01-20
```

#### Analysis Field Description

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Stock ticker symbol |
| `weeks_above_1_week_ago` | int | Number of weeks where closing price was higher than 1 week prior |
| `weeks_above_2_weeks_ago` | int | Number of weeks where closing price was higher than 2 weeks prior |
| `weeks_above_4_weeks_ago` | int | Number of weeks where closing price was higher than 4 weeks prior |
| `biggest_weekly_jump_pct` | float | Largest week-over-week percentage increase |
| `biggest_weekly_drop_pct` | float | Largest week-over-week percentage decrease |
| `biggest_biweekly_jump_pct` | float | Largest biweekly (2-week) percentage increase |
| `biggest_biweekly_drop_pct` | float | Largest biweekly (2-week) percentage decrease |
| `biggest_monthly_jump_pct` | float | Largest monthly (4-week) percentage increase |
| `biggest_monthly_drop_pct` | float | Largest monthly (4-week) percentage decrease |
| `change_1y_pct` | float | Percentage change over 1 year (52 weeks) |
| `change_6m_pct` | float | Percentage change over 6 months (26 weeks) |
| `change_3m_pct` | float | Percentage change over 3 months (13 weeks) |
| `change_1m_pct` | float | Percentage change over 1 month (4 weeks) |
| `total_weeks` | int | Total number of weeks analyzed |
| `linear_slope_pct` | float | Linear trend slope as percentage of starting price per week |
| `linear_r_squared` | float | R² value (0-1) indicating how well the price data fits the linear trend line (higher = more consistent trend) |
| `log_slope` | float | Annualized log trend slope (log slope * 52 weeks per year) |
| `log_r_squared` | float | R² value (0-1) indicating how well the price data fits the log trend line (higher = more consistent trend) |

### Pick 
```bash
Usage: python -m stockpick.cli pick [OPTIONS]

  Apply a rule onto analyzed stock prices for a given date range.

Options:
  -d, --date TEXT                 Analysis date in YYYY-MM-DD format
  -r, --rule TEXT                 Rule expression string (e.g., 'change_3m_pct
                                  > 10 AND biggest_biweekly_drop_pct > 15')
                                  [required]
  -m, --max-stocks INTEGER        Maximum number of stocks to hold at once
                                  (default: 3)
  -i, --index [SP500|DOWJONES|NASDAQ]
                                  Stock index to analyze
  --help                          Show this message and exit.

# Example
uv run python -m stockpick.cli pick -r 'change_3m_pct > 10 AND biggest_biweekly_drop_pct > 1'
```

### Simulate
```bash
Usage: python -m stockpick.cli simulate [OPTIONS]

  Simulate investment strategy for a given date range.

Options:
  --max-stocks INTEGER            Maximum number of stocks to hold at once
                                  (default: 3)
  --rebalance-interval-weeks INTEGER
                                  Rebalance interval in weeks (default: 2)
  --date-start TEXT               Simulation start date in YYYY-MM-DD format
                                  [required]
  --date-end TEXT                 Simulation end date in YYYY-MM-DD format
                                  [required]
  -i, --index [SP500|DOWJONES|NASDAQ]
                                  Stock index to analyze
  -r, --rule TEXT                 Rule expression string (e.g., 'change_3m_pct
                                  > 10 AND biggest_biweekly_drop_pct > 15')
  --help                          Show this message and exit.
  
# Example
uv run python -m stockpick.cli simulate --max-stocks=3 --rebalance-interval-weeks=4 --date-start=2022-01-01 --date-end=2026-01-20 --rule='change_3m_pct > 10'
```
