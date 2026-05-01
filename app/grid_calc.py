#!/usr/bin/env python3
"""
Grid trading calculator for USD/JPY.

Calculates required margin and unrealized P&L when the rate reaches a specified price,
assuming positions are taken at 5-pip intervals between upper and lower bounds.
"""

import argparse

PIP = 0.01
GRID_STEP = 5 * PIP
CONTRACT_SIZE = 100_000  # 1 lot = 100,000 USD


def build_grid_levels(lower: float, upper: float) -> list[float]:
    """Return grid price levels from lower to upper at 5-pip intervals."""
    levels = []
    price = round(lower * 100) / 100
    upper_rounded = round(upper * 100) / 100
    while price <= upper_rounded + 1e-9:
        levels.append(round(price * 100) / 100)
        price = round((price + GRID_STEP) * 100) / 100
    return levels


def calc_margin(lot: float, entry: float, leverage: int, currency: str) -> float:
    """Margin in account currency. JPY: USD position converted at entry rate. USD: raw USD."""
    if currency == "JPY":
        return lot * CONTRACT_SIZE * entry / leverage
    else:
        return lot * CONTRACT_SIZE / leverage


def calc_pnl(entry: float, rate: float, lot: float, direction: str, currency: str) -> float:
    """P&L in account currency. JPY: raw JPY. USD: JPY P&L converted at current rate."""
    price_diff = (rate - entry) if direction == "buy" else (entry - rate)
    pnl_jpy = price_diff * lot * CONTRACT_SIZE
    return pnl_jpy if currency == "JPY" else pnl_jpy / rate


def calc_buy(levels: list[float], rate: float, lot: float, leverage: int, currency: str) -> list[dict]:
    """
    Buy grid: buy limits are filled as price falls.
    When price = rate, positions at levels >= rate are open.
    """
    open_positions = [lvl for lvl in levels if lvl >= rate - 1e-9]
    result = []
    for entry in open_positions:
        result.append({
            'entry': entry,
            'margin': calc_margin(lot, entry, leverage, currency),
            'pnl': calc_pnl(entry, rate, lot, 'buy', currency),
        })
    return result


def calc_sell(levels: list[float], rate: float, lot: float, leverage: int, currency: str) -> list[dict]:
    """
    Sell grid: sell limits are filled as price rises.
    When price = rate, positions at levels <= rate are open.
    """
    open_positions = [lvl for lvl in levels if lvl <= rate + 1e-9]
    result = []
    for entry in open_positions:
        result.append({
            'entry': entry,
            'margin': calc_margin(lot, entry, leverage, currency),
            'pnl': calc_pnl(entry, rate, lot, 'sell', currency),
        })
    return result


def print_results(direction: str, rate: float, positions: list[dict], lot: float, leverage: int, currency: str):
    total_margin = sum(p['margin'] for p in positions)
    total_pnl = sum(p['pnl'] for p in positions)
    total_lots = lot * len(positions)

    def fmt(value: float) -> str:
        if currency == "JPY":
            return f"{value:,.0f} JPY  ({value / 10_000:.2f} 万円)"
        else:
            return f"{value:,.2f} USD"

    print(f"\n=== {direction.upper()} Grid at rate {rate:.3f} ===")
    print(f"Leverage      : {leverage}x")
    print(f"Lot per grid  : {lot}")
    print(f"Open positions: {len(positions)}")
    print(f"Total lots    : {total_lots:.3f}")
    print(f"Total margin  : {fmt(total_margin)}")
    print(f"Total P&L     : {fmt(total_pnl)}")

    cur = currency
    if positions:
        print(f"\n{'Entry':>8}  {'Pips':>6}  {'Margin (' + cur + ')':>14}  {'P&L (' + cur + ')':>14}")
        print("-" * 50)
        for p in positions:
            pips = (rate - p['entry']) / PIP if direction == 'buy' else (p['entry'] - rate) / PIP
            decimals = 0 if currency == "JPY" else 2
            print(f"{p['entry']:>8.3f}  {pips:>+6.1f}  {p['margin']:>14,.{decimals}f}  {p['pnl']:>14,.{decimals}f}")
        print("-" * 50)
        decimals = 0 if currency == "JPY" else 2
        print(f"{'Total':>8}  {'':>6}  {total_margin:>14,.{decimals}f}  {total_pnl:>14,.{decimals}f}")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate required margin and unrealized P&L for USD/JPY grid trading"
    )
    parser.add_argument("--upper",     type=float, required=True,  help="Upper price limit")
    parser.add_argument("--lower",     type=float, required=True,  help="Lower price limit")
    parser.add_argument("--lot",       type=float, required=True,  help="Lot size per grid position")
    parser.add_argument("--rate",      type=float, required=True,  help="Current rate")
    parser.add_argument("--leverage",  type=int,   default=1000,   help="Leverage (default: 1000)")
    parser.add_argument("--direction", choices=["buy", "sell", "both"], default="buy",
                        help="Grid direction (default: buy)")
    parser.add_argument("--currency", choices=["JPY", "USD"], default="JPY",
                        help="Account base currency (default: JPY)")
    args = parser.parse_args()

    if args.lower >= args.upper:
        parser.error("--lower must be less than --upper")
    if args.rate < args.lower or args.rate > args.upper:
        print(f"Warning: rate {args.rate} is outside [{args.lower}, {args.upper}]")

    levels = build_grid_levels(args.lower, args.upper)
    print(f"Grid range    : {args.lower:.3f} ~ {args.upper:.3f}")
    print(f"Grid levels   : {len(levels)} (every 5 pips)")
    print(f"Base currency : {args.currency}")

    if args.direction in ("buy", "both"):
        positions = calc_buy(levels, args.rate, args.lot, args.leverage, args.currency)
        print_results("buy", args.rate, positions, args.lot, args.leverage, args.currency)

    if args.direction in ("sell", "both"):
        positions = calc_sell(levels, args.rate, args.lot, args.leverage, args.currency)
        print_results("sell", args.rate, positions, args.lot, args.leverage, args.currency)


if __name__ == "__main__":
    main()
