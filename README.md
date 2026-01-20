
### Analyze
```bash
Usage: python -m stockpick.cli analyze [OPTIONS] DATE

# Example
uv run python -m stockpick.cli analyze 2026-01-20
```


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
  --help                          Show this message and exit.

# Example
uv run python -m stockpick.cli simulate --max-stocks=3 --rebalance-interval-weeks=4 --date-start=2022-01-01 --date-end=2026-01-20
```
