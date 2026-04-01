#!/usr/bin/env python3
"""
Required margin calculator for USD/JPY grid trading.

Calculates required margin when the rate reaches a specified price,
assuming positions are taken at 5-pip intervals between upper and lower bounds.
"""

import argparse

PIP = 0.01       # 1 pip for USD/JPY
GRID_STEP = 5 * PIP   # 5 pips
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


def calc_margin_buy(levels: list[float], rate: float, lot: float, leverage: int) -> list[dict]:
    """
    Buy grid: buy limits are filled as price falls.
    When price = rate, positions at levels >= rate are open.
    """
    open_positions = [lvl for lvl in levels if lvl >= rate - 1e-9]
    result = []
    for entry in open_positions:
        margin_jpy = lot * CONTRACT_SIZE * entry / leverage
        result.append({'entry': entry, 'margin_jpy': margin_jpy})
    return result


def calc_margin_sell(levels: list[float], rate: float, lot: float, leverage: int) -> list[dict]:
    """
    Sell grid: sell limits are filled as price rises.
    When price = rate, positions at levels <= rate are open.
    """
    open_positions = [lvl for lvl in levels if lvl <= rate + 1e-9]
    result = []
    for entry in open_positions:
        margin_jpy = lot * CONTRACT_SIZE * entry / leverage
        result.append({'entry': entry, 'margin_jpy': margin_jpy})
    return result


def print_results(direction: str, rate: float, positions: list[dict], lot: float, leverage: int):
    total_margin = sum(p['margin_jpy'] for p in positions)
    total_lots = lot * len(positions)

    print(f"\n=== {direction.upper()} Grid Margin at rate {rate:.3f} ===")
    print(f"Leverage     : {leverage}x")
    print(f"Lot per grid : {lot}")
    print(f"Open positions: {len(positions)}")
    print(f"Total lots   : {total_lots:.3f}")
    print(f"Total margin : {total_margin:,.0f} JPY  ({total_margin / 10_000:.2f} 万円)")

    if positions:
        print(f"\n{'Entry':>8}  {'Margin (JPY)':>14}")
        print("-" * 26)
        for p in positions:
            print(f"{p['entry']:>8.3f}  {p['margin_jpy']:>14,.0f}")
        print("-" * 26)
        print(f"{'Total':>8}  {total_margin:>14,.0f}")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate required margin for USD/JPY grid trading"
    )
    parser.add_argument("--upper",     type=float, required=True,  help="Upper price limit")
    parser.add_argument("--lower",     type=float, required=True,  help="Lower price limit")
    parser.add_argument("--lot",       type=float, required=True,  help="Lot size per grid position")
    parser.add_argument("--rate",      type=float, required=True,  help="Rate to calculate margin at")
    parser.add_argument("--leverage",  type=int,   default=1000,   help="Leverage (default: 1000)")
    parser.add_argument("--direction", choices=["buy", "sell", "both"], default="buy",
                        help="Grid direction (default: buy)")
    args = parser.parse_args()

    if args.lower >= args.upper:
        parser.error("--lower must be less than --upper")
    if args.rate < args.lower or args.rate > args.upper:
        print(f"Warning: rate {args.rate} is outside [{args.lower}, {args.upper}]")

    levels = build_grid_levels(args.lower, args.upper)
    print(f"Grid range   : {args.lower:.3f} ~ {args.upper:.3f}")
    print(f"Grid levels  : {len(levels)} (every 5 pips)")

    if args.direction in ("buy", "both"):
        positions = calc_margin_buy(levels, args.rate, args.lot, args.leverage)
        print_results("buy", args.rate, positions, args.lot, args.leverage)

    if args.direction in ("sell", "both"):
        positions = calc_margin_sell(levels, args.rate, args.lot, args.leverage)
        print_results("sell", args.rate, positions, args.lot, args.leverage)


if __name__ == "__main__":
    main()
