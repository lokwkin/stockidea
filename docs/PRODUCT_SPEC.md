# Stockidea — Product Specification

## Overview

**Stockidea** is a systematic stock strategy backtesting platform. It allows users to design rule-based stock selection strategies, run historical simulations, and analyze performance against market benchmarks. The platform emphasizes realistic, point-in-time backtesting and transparent strategy evaluation.



## 1. Strategy Backtesting (Simulation)

Stockidea enables users to configure and execute historical simulations to evaluate stock selection strategies over a defined period.

### Configuration Options

- **Stock Index**: Universe of stocks (S&P 500, Dow Jones, NASDAQ)
- **Maximum Stocks**: Maximum number of stocks held concurrently (default: 3)
- **Rebalance Interval**: Portfolio rebalance frequency in weeks (default: 2)
- **Date Range**: Simulation start and end dates
- **Selection Rule**: Boolean rule expression defining eligible stocks

### Simulation Flow

1. **Initial Setup**
   - Simulation begins with a virtual balance of **$10,000**

2. **Periodic Rebalancing**
   - On each rebalance date:
     - Analyze all stocks in the selected index
     - Filter stocks using the user-defined rule
     - Rank qualifying stocks by *rising stability*
     - Remove statistical outliers
     - Allocate capital equally across the top N stocks

3. **Performance Tracking**
   - Track profit and loss per investment
   - Compare total portfolio return against an S&P 500 baseline



## 2. Rule-Based Stock Selection

Users define stock eligibility using rule expressions evaluated independently for each stock.

### Available Metrics

#### Price Change Metrics
- `change_1w_pct`, `change_2w_pct`
- `change_1m_pct`, `change_3m_pct`
- `change_6m_pct`, `change_1y_pct`

#### Volatility Metrics
- `max_jump_1w_pct`, `max_drop_1w_pct`
- `max_jump_2w_pct`, `max_drop_2w_pct`
- `max_jump_4w_pct`, `max_drop_4w_pct`

#### Trend Metrics
- `linear_slope_pct` — Weekly linear trend (% of starting price)
- `linear_r_squared` — Linear trend consistency (0–1)
- `log_slope` — Annualized logarithmic growth rate
- `log_r_squared` — Exponential trend fit quality (0–1)

#### Other
- `total_weeks` — Number of weeks of available data
- `symbol` — Stock ticker symbol

### Rule Syntax

Rules support:
- Comparison operators: `>`, `<`, `>=`, `<=`, `==`, `!=`
- Logical operators: `AND`, `OR`, `NOT`
- Parentheses for grouping

### Example Rules
```
change_3m_pct > 10
change_3m_pct > 10 AND max_drop_2w_pct > -5
linear_r_squared > 0.8 AND linear_slope_pct > 0.5
change_1m_pct > 0 AND change_3m_pct > 0 AND change_6m_pct > 0
```



## 3. Stock Ranking System

After filtering by rules, remaining stocks are ranked to determine final selections.

### Rising Stability Score

The ranking score combines:
- **Trend Strength** — Normalized linear slope (rate of price increase)
- **Trend Consistency** — R-squared value (smoothness and predictability)

Stocks with strong and consistent upward trends rank highest. Extreme statistical outliers are automatically removed before final selection.



## 4. Trend Analysis Engine

Each stock is analyzed using its trailing 52-week price history to compute all metrics used for filtering and ranking.

### Analysis Includes

- Weekly price aggregation from daily data
- Multi-horizon return calculations
- Detection of maximum gains and losses
- Linear and logarithmic regression analysis
- Data quality checks (minimum 5 weeks required)

Analysis results are cached to improve performance for repeated simulations.



## 5. Historical Accuracy & Data Integrity

Stockidea uses point-in-time data to ensure realistic backtesting.

- **Index Constituents**: Actual index membership at each historical date
- **Historical Prices**: Dividend-adjusted closing prices
- **Trading Day Handling**: Rebalance dates automatically adjust to valid trading days



## 6. Dashboard Features

### Simulation Results View

- **Performance Summary**
  - Final portfolio value
  - Total profit/loss (absolute and percentage)
  - Comparison vs S&P 500 return

- **Balance History Chart**
  - Portfolio value over time
  - Rebalance markers with drill-down details
  - Baseline performance overlay

- **Investment Tables**
  - Individual investment breakdown
  - Aggregated performance by rebalance period

- **Detailed Metrics**
  - Top winners and losers
  - Buy/sell prices and dates
  - Profit/loss per position

### Rebalance Detail View

- Selected stocks and their metrics
- Individual investment performance
- Buy and sell execution details

### Trend Analysis Browser

- Browse historical analysis snapshots
- Filter stocks using rule expressions
- Sort by any metric
- Symbol search and highlighting



## 7. Supported Stock Indices

- **S&P 500** — 500 largest US companies
- **Dow Jones** — 30 major industrial companies
- **NASDAQ** — Technology and growth stocks



## 8. Data Coverage

- **Historical Prices**: 2011 to present
- **Index Membership**: Historical constituent changes tracked
- **Data Refresh**: Prices updated daily on access



## 9. Primary Use Cases

- Strategy discovery and validation
- Parameter optimization (rebalance interval, portfolio size)
- Risk management using volatility constraints
- Momentum and trend-following strategies
- Performance comparison against passive index investing