# Stockidea

Stockidea is a platform for designing and backtesting systematic stock strategies using transparent, composable signals, allowing user to build rule-based portfolios with momentum, trend, volatility, liquidity, and fundamental indicators while evaluating performance under realistic rebalancing and risk constraints.

## Dashboard
The frontend dashboard allows users to define custom strategy configurations, run simulations, and inspect detailed analytics for each rebalance action at every point in time.

<img src="docs/dashboard.gif" alt="Dashboard" width="60%">


## Setup local development

First clone a `.env` from `.env.example` and supply your own credentials.

Then start database, backend and frontend container using docker compose
```
docker-compose up -d
```

## Command Line APIs

### Analyze
Analyze the stock price and performance data of index constituent stocks at a given date with the data in the past 52 weeks.

#### Example
```bash
uv run python -m stockidea.cli analyze -d 2026-01-20
```

#### Options
```
  -d, --date TEXT                 Analysis date in YYYY-MM-DD format
  -i, --index [SP500|DOWJONES|NASDAQ]
                                  Stock index to analyze
```

### Pick
Analyze the stock price and indicator data of index constituent stocks at a given date with the data in the past 52 weeks, then filter and pick the stocks based on user's custom rule.

#### Example
```bash
uv run python -m stockidea.cli pick -r 'change_3m_pct > 10 AND biggest_biweekly_drop_pct > 1'
```

#### Options
```
  -d, --date TEXT                 Analysis date in YYYY-MM-DD format
  -r, --rule TEXT                 Rule expression string (e.g., 'change_3m_pct
                                  > 10 AND biggest_biweekly_drop_pct > 15')
                                  [required]
  -m, --max-stocks INTEGER        Maximum number of stocks to hold at once
                                  (default: 3)
  -i, --index [SP500|DOWJONES|NASDAQ]
                                  Stock index to analyze
```

### Simulate
With user's custom rules, backtest and simulate the performance within the given date range.

#### Example
```bash
uv run python -m stockidea.cli simulate --max-stocks=3 --rebalance-interval-weeks=4 --date-start=2022-01-01 --date-end=2026-01-20 --rule='change_3m_pct > 10'
```

#### Options
```
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
```

## Stock Picking Rule and Available Performance Data
The analysis will result in a list of performance data for each stock. User can design stock filtering / picking rule using the field below. 

For example, `change_3m_pct > 10 AND biggest_biweekly_drop_pct > 15` means on each rebalance point, only pick the stocks that has 3 months percentage change larger than 10% and the biggest bi-weekly drop percentage less than 15%.

### Field Descriptions

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

## Upcoming
- Add more stock indicator and signals
  - Trend and momentum data (Returns, Moving Averages, Breakouts, Strength)
  - Volatility and Risks
  - Volume and Liquidity (later phase)
  - Fundamentals (PE, PB, EV/EBITDA)
  - Market context (sector)
- Allow custom stock ranking logic for stocks satisfying the rules.
- Add exit criteria and mechanism in simulation
- Add LLM assisted strategy design
- Automated strategy tuning

## License
This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.