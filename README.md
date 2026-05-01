# fx_utils

FX utilities for USD/JPY: data collection, price notifications, and MT4/MT5 EA settings generation.

## Usage

```bash
docker compose run --rm dev python <script_name>.py
```

### margin_calc.py

```bash
docker compose run --rm dev python grid_calc.py \
  --upper 152.00 --lower 148.00 --lot 0.07 --rate 148.00
```

Options: `--leverage` (default: 1000), `--direction buy|sell|both` (default: buy)

See [CLAUDE.md](CLAUDE.md) for details.
