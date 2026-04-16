# CLAUDE.md

FX utilities for USD/JPY: data collection, price notifications, MT4/MT5 EA settings generation, and account management.

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
| `grid_calc.py` | Calculate required margin and unrealized P&L for USD/JPY grid trading |
| `account_manager.py` | Import account records (Deposit/Withdrawal/Closed P&L/Equity) from CSV into SQLite |

## Directory Structure

```
data/
  db/usdjpy.db            # USD/JPY price database
  db/accounts.db          # Account records database
  input/account/data.csv  # Account records input (CSV)
  input/pos/exness.txt    # MT5 position data (Exness)
  input/pos/hfm.txt       # MT5 position data (HFM)
  output/sets/exness/     # Generated .set files
  output/sets/hfm/        # Generated .set files
  output/sets/oanda/      # Generated .set files
```

## Database Schema

### `usdjpy.db`

**usdjpy_hourly** — raw hourly OHLC, PK: `timestamp` (ISO 8601 UTC)

**usdjpy_daily** — aggregated daily OHLC, PK: `date` (YYYY-MM-DD)
- Open/Close: first/last hourly record; High/Low: max/min; Volume: sum

### `accounts.db`

**account_records** — PK: `id`
- `account` TEXT — account name (e.g. exness, hfm, oanda)
- `date` TEXT — YYYY-MM-DD
- `record_type` TEXT — `deposit` / `withdrawal` / `closed_pnl` / `equity`
- `amount` REAL — withdrawal is always stored as negative

## Key Details

- Timestamps stored in UTC (timezone-aware via pytz)
- Fetch period: `start` param in `fetch_usdjpy_hourly()` (Yahoo Finance intraday data limited to ~730 days)
- `account_manager.py` reads `/data/input/account/data.csv` (header: `account,type,date,amount,note`); date format is `YYYY.MM.DD`; full replace on each run
