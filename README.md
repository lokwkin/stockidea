# Stockpick


### Start API
```
uv run python -m stockpick.api
```

### Analyze
```bash
Usage: python -m stockpick.cli analyze [OPTIONS] [DATE]

  Analyze stock prices for a given date. If no date is provided, the current
  date is used.

# Example
uv run python -m stockpick.cli analyze 2026-01-20
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
| `trend_slope_pct` | float | Linear trend slope as percentage of starting price per week |
| `trend_r_squared` | float | R² value (0-1) indicating how well the price data fits the trend line (higher = more consistent trend) |




### Simulate
```bash
Usage: python -m stockpick.cli simulate [OPTIONS]

Options:
  --max-stocks INTEGER            Maximum number of stocks to hold at once
                                  (default: 3)
  --rebalance-interval-weeks INTEGER
                                  Rebalance interval in weeks (default: 2)
  --date-start TEXT               Simulation start date in YYYY-MM-DD format
                                  [required]
  --date-end TEXT                 Simulation end date in YYYY-MM-DD format
                                  [required]

# Example
uv run python -m stockpick.cli simulate --max-stocks=3 --rebalance-interval-weeks=4 --date-start=2022-01-01 --date-end=2026-01-20
```
