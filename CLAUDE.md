# CLAUDE.md

FX utilities for USD/JPY, AUD/JPY and AUD/USD: data collection, price notifications, MT4/MT5 EA settings generation, and account management.

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
| `fetch_daily.py` | Fetch daily OHLC for USD/JPY, AUD/JPY and AUD/USD from Yahoo Finance, save to SQLite; optional `--start` |
| `daily_price_notify.py` | Fetch latest USD/JPY price + Bollinger Bands from `fx_daily.db`, send to Discord |
| `generate_grid_settings.py` | Generate MT4/MT5 EA grid `.set` files for multiple pairs (USD/JPY, AUD/JPY, AUD/USD) from `fx_daily.db` |
| `position_analysis.py` | Analyze MT5 positions (avg execution price for buy/sell) from all `*.txt` in `/data/input/pos/` |
| `grid_calc.py` | Calculate required margin and unrealized P&L for USD/JPY grid trading — requires `--upper`, `--lower`, `--lot`, `--rate`; optional `--leverage` (default 1000), `--direction` buy/sell/both, `--currency` JPY/USD |
| `account_manager.py` | Import account records (Deposit/Profit/Equity) from TSV into SQLite |

## Environment Variables

### `generate_grid_settings.py`

All variables are pair-prefixed (`{PAIR}` = `USDJPY`, `AUDJPY`, `AUDUSD`, etc.).

| Variable | Default | Description |
|----------|---------|-------------|
| `PAIRS` | _(required)_ | Comma-separated list of pairs to process |
| `{PAIR}_ACCOUNTS` | _(none)_ | `name:lot[:sell_enabled]` comma-separated; controls output dirs |
| `{PAIR}_MAGIC_NUMBER` | `8001` | Magic number for the grid EA |
| `{PAIR}_GRID_STEP_PIPS` | `5` | Grid step size in pips |
| `{PAIR}_GRID_CENTER_ADJUSTMENT` | `0` | % adjustment to previous close for center price |
| `{PAIR}_GRID_RANGE` | `1` | Range % of previous close for buy/sell pips |
| `{PAIR}_GRID_CENTER_MAX` | _(none)_ | Hard cap on center price |
| `{PAIR}_GRID_CENTER_MIN` | _(none)_ | Hard floor on center price |

### Common

| Variable | Description |
|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Used by `daily_price_notify.py` |

## Directory Structure

```
data/
  db/fx_daily.db            # Multi-pair daily OHLC (USD/JPY, AUD/USD via fetch_daily.py)
  db/accounts.db            # Account records database
  input/account/data.tsv    # Account records input (TSV)
  input/pos/<account>.txt   # MT5 position data (one file per account, e.g. exness.txt, icmarkets.txt)
  output/sets/<account>/    # Generated .set files (dirs created from {PAIR}_ACCOUNTS env var)
```

## Database Schema

### `fx_daily.db`

**fx_daily** — daily OHLC for multiple pairs, PK: `(pair, date)`
- `pair` TEXT — e.g. `USDJPY`, `AUDUSD`, `AUDJPY`
- `date` TEXT — YYYY-MM-DD
- `open`, `high`, `low`, `close` REAL
- `created_at` TEXT — ISO datetime

### `accounts.db`

**account_records** — PK: `id`
- `account` TEXT — account name (e.g. exness, hfm, oanda)
- `date` TEXT — YYYY-MM-DD
- `record_type` TEXT — `profit` / `equity` / `deposit`
- `amount` REAL
- `note` TEXT — optional

## Key Details

- `fetch_daily.py` defaults to last 60 days; use `--start YYYY-MM-DD` for historical data
- `account_manager.py` reads `/data/input/account/data.tsv` (header: `account\ttype\tdate\tamount\tnote`); date format is `YYYY.MM.DD`; full replace on each run
