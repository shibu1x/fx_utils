# CLAUDE.md

FX utilities for multiple currency pairs: OHLC data collection, MT4/MT5 EA settings generation, and daily range analysis.

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
| `fetch.py` | Fetch daily OHLC data for FX pairs from Yahoo Finance, save to SQLite; optional positional `[PAIR ...]` (default: USDJPY) |
| `grid_settings.py` | Generate MT4/MT5 EA grid `.set` files for multiple pairs from `fx_utils.db` |
| `grid_calc.py` | Calculate required margin and unrealized P&L for USD/JPY grid trading — requires `--upper`, `--lower`, `--lot`, `--rate`; optional `--leverage` (default 1000), `--direction` buy/sell/both, `--currency` JPY/USD, `--grid-step` (default 5) |
| `daily_range_analysis.py` | Analyze daily high/low % change from open; optional `--pair`, `--start`, `--end`; outputs TSV to `data/output/daily_range_analysis.tsv` |

## Environment Variables

### `grid_settings.py`

All variables are pair-prefixed (`{PAIR}` = `USDJPY`, `AUDJPY`, `AUDUSD`, `GBPUSD`, etc.).

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

## Directory Structure

```
data/
  db/fx_utils.db                      # Multi-pair daily OHLC data (via fetch.py)
  output/sets/<account>/              # Generated .set files (dirs from {PAIR}_ACCOUNTS)
  output/daily_range_analysis.tsv     # Daily range analysis output
```

## Database Schema

### `fx_utils.db`

**price_history** — daily OHLC data for multiple pairs, PK: `(pair, date)`
- `pair` TEXT — e.g. `USDJPY`, `AUDUSD`, `AUDJPY`, `GBPUSD`
- `date` TEXT — YYYY-MM-DD
- `open` REAL
- `high` REAL
- `low` REAL
- `close` REAL
