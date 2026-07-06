#!/usr/bin/env python3
"""
Calculate unrealized P&L of existing positions at a specified rate.

Reads open positions from an MT4/MT5 tab-separated report export
(data/input/pos.txt) and computes profit/loss for each position
if the rate moves to --rate. Assumes JPY-quoted pairs (e.g. USDJPY).
"""

import argparse
from pathlib import Path

PIP = 0.01
CONTRACT_SIZE = 100_000  # 1 lot = 100,000 units of base currency
DEFAULT_INPUT = Path("/data/input/pos.txt")


def parse_positions(path: Path, pair: str | None) -> list[dict]:
    positions = []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines[1:]:  # skip header row
        fields = [f.strip() for f in line.strip("\n").split("\t")]
        if len(fields) < 6:
            continue
        _open_time, ticket, type_, size, item, price = fields[:6]
        if type_ not in ("buy", "sell"):
            continue
        if pair and item != pair:
            continue
        positions.append({
            "ticket": ticket,
            "type": type_,
            "size": float(size),
            "item": item,
            "price": float(price),
        })
    return positions


def calc_pnl(entry: float, rate: float, size: float, direction: str) -> float:
    price_diff = (rate - entry) if direction == "buy" else (entry - rate)
    return price_diff * size * CONTRACT_SIZE


def main():
    parser = argparse.ArgumentParser(
        description="Calculate unrealized P&L of existing positions at a specified rate"
    )
    parser.add_argument("--rate", type=float, required=True, help="Target rate to evaluate P&L at")
    parser.add_argument("--pair", help="Filter positions by pair (e.g. USDJPY); default: all pairs in file")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"Input file path (default: {DEFAULT_INPUT})")
    args = parser.parse_args()

    positions = parse_positions(args.input, args.pair)
    if not positions:
        print("No positions found.")
        return

    pairs = sorted({p["item"] for p in positions})
    if len(pairs) > 1:
        print(f"Warning: multiple pairs found in input ({', '.join(pairs)}); applying --rate to all")

    print(f"\n=== Unrealized P&L at rate {args.rate:.3f} ===")
    print(f"{'Ticket':>12}  {'Type':>4}  {'Item':>8}  {'Size':>6}  {'Entry':>8}  {'Pips':>7}  {'P&L':>12}")
    print("-" * 70)

    total_pnl = 0.0
    total_size = 0.0
    for p in positions:
        pnl = calc_pnl(p["price"], args.rate, p["size"], p["type"])
        pips = (args.rate - p["price"]) / PIP if p["type"] == "buy" else (p["price"] - args.rate) / PIP
        total_pnl += pnl
        total_size += p["size"]
        print(f"{p['ticket']:>12}  {p['type']:>4}  {p['item']:>8}  {p['size']:>6.2f}  "
              f"{p['price']:>8.3f}  {pips:>+7.1f}  {pnl:>12,.0f}")

    print("-" * 70)
    print(f"{'Total':>12}  {'':>4}  {'':>8}  {total_size:>6.2f}  {'':>8}  {'':>7}  {total_pnl:>12,.0f}")
    print(f"\nPositions: {len(positions)}")
    print(f"Total P&L: {total_pnl:,.0f} JPY  ({total_pnl / 10_000:.2f} 万円)")


if __name__ == "__main__":
    main()
