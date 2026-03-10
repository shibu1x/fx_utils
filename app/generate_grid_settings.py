#!/usr/bin/env python3
"""
Generate grid settings .set files for MT4/MT5 EA.
Creates two files with different LotSize values (0.07 and 0.03).
"""

import os
import sqlite3
from datetime import date


def parse_float_env(key, default):
    value_str = os.environ.get(key, str(default))
    try:
        return float(value_str)
    except ValueError:
        print(f"Warning: Invalid {key} value '{value_str}', using {default}")
        return float(default)


def round_to_2_or_7(value):
    """
    Round value to 2 decimal places where the second decimal is 2 or 7.
    Candidates: .02, .07, .12, .17, .22, .27, ...
    """
    cents = round(value * 100)
    q = cents // 5
    new_cents = q * 5 + 2
    return new_cents / 100


def fetch_recent_closes(conn, days=20):
    today = date.today().isoformat()
    query = """
        SELECT date, close
        FROM usdjpy_daily
        WHERE date < ?
        ORDER BY date DESC
        LIMIT ?
    """
    cursor = conn.execute(query, (today, days))
    return cursor.fetchall()


def calculate_bollinger_bands(closes, period=20):
    if len(closes) < period:
        return None

    prices = closes[:period]
    sma = sum(prices) / period
    variance = sum((p - sma) ** 2 for p in prices) / period
    std_dev = variance ** 0.5

    return {
        'sma': sma,
        'upper_2': sma + (2 * std_dev),
        'upper_1': sma + (1 * std_dev),
        'lower_1': sma - (1 * std_dev),
        'lower_2': sma - (2 * std_dev),
    }


def calculate_center_price(previous_close, adjustment_pct, upper_2, lower_2):
    center = previous_close * (1 + adjustment_pct / 100)
    return max(lower_2, min(upper_2, center))


def write_set_file(filepath, lot_size, center_price, sell_range_pips, buy_range_pips, sell_enabled=True):
    sell_str = 'true' if sell_enabled else 'false'
    content = f"""; === Basic Settings ===
GridStepPips=5
UseTakeProfit=true
LotSize={lot_size}
GridRange=4
MagicNumber=8001
; === Sell Grid Settings ===
SellEnabled={sell_str}
; === Buy Grid Settings ===
BuyEnabled=true

GridCenterPrice={center_price:.2f}
SellRangePips={sell_range_pips}
BuyRangePips={buy_range_pips}
"""
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Written: {filepath}")


def main():
    conn = sqlite3.connect('data/db/usdjpy.db')

    adjustment = parse_float_env('CENTER_PRICE_ADJUSTMENT', 0)
    range_percent = parse_float_env('RANGE_PIPS_PERCENT', 1)
    os.makedirs('data/sets/mt5a1', exist_ok=True)
    os.makedirs('data/sets/mt5a2', exist_ok=True)
    os.makedirs('data/sets/mt5a4', exist_ok=True)

    try:
        rows = fetch_recent_closes(conn, days=20)

        if not rows:
            print("Error: No data available")
            return

        previous_date = rows[0][0]
        previous_close = rows[0][1]
        closes = [row[1] for row in rows]

        bands = calculate_bollinger_bands(closes)

        if bands is None:
            print("Error: Insufficient data for Bollinger Bands calculation")
            return

        center_price = calculate_center_price(
            previous_close, adjustment, bands['upper_2'], bands['lower_2']
        )
        rounded_center = round_to_2_or_7(center_price)

        adjustment_price = previous_close * adjustment / 100
        adjustment_pips = round(adjustment_price * 100)
        base_pips = round(previous_close * range_percent)
        sell_range_pips = base_pips - adjustment_pips
        buy_range_pips = base_pips + adjustment_pips

        print(f"Date: {previous_date}")
        print(f"Previous Close: {previous_close:.2f}")
        print(f"GridCenterPrice: {rounded_center:.2f}")
        print(f"SellRangePips: {sell_range_pips}")
        print(f"BuyRangePips: {buy_range_pips}")

        write_set_file(
            'data/sets/mt5a1/grid_lot7.set',
            0.07, rounded_center, sell_range_pips, buy_range_pips
        )
        write_set_file(
            'data/sets/mt5a2/grid_lot1.set',
            0.01, rounded_center, sell_range_pips, buy_range_pips, sell_enabled=False
        )
        write_set_file(
            'data/sets/mt5a4/grid_lot3.set',
            0.03, rounded_center, sell_range_pips, buy_range_pips
        )

    finally:
        conn.close()


if __name__ == '__main__':
    main()
