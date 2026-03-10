# CLAUDE.md

FX utilities for USD/JPY: data collection, price notifications, and MT4/MT5 EA settings generation.

## Development Environment

Docker containers exclusively. Run scripts via Docker Compose:

```bash
docker compose run --rm dev python <script_name>.py
docker compose run --rm dev /bin/bash  # interactive shell
docker compose build dev               # build image
task build                             # production build
```

## Scripts

| Script | Description |
|--------|-------------|
| `fetch_usdjpy.py` | Fetch hourly OHLC from Yahoo Finance, aggregate to daily, save to SQLite |
| `daily_price_notify.py` | Fetch latest price + Bollinger Bands, send to Discord |
| `generate_grid_settings.py` | Generate MT4/MT5 EA grid `.set` files from recent price data |
| `position_analysis.py` | Analyze MT5 positions (avg execution price for buy/sell) |

## Directory Structure

```
app/data/
  db/usdjpy.db       # SQLite database
  pos/exness.txt     # MT5 position data (Exness)
  pos/hfm.txt        # MT5 position data (HFM)
  sets/mt5a1/        # Generated .set files
  sets/mt5a4/        # Generated .set files
```

## Database Schema (`app/data/db/usdjpy.db`)

**usdjpy_hourly** — raw hourly OHLC, PK: `timestamp` (ISO 8601 UTC)

**usdjpy_daily** — aggregated daily OHLC, PK: `date` (YYYY-MM-DD)
- Open/Close: first/last hourly record; High/Low: max/min; Volume: sum

## Key Details

- Timestamps stored in UTC (timezone-aware via pytz)
- Fetch period: `start`/`end` params in `fetch_usdjpy_hourly()` (currently 2024-04-01 to 2025-12-22)
- Yahoo Finance intraday data limited to ~730 days
