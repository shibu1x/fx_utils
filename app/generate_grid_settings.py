#!/usr/bin/env python3
"""
Generate grid settings .set files for MT4/MT5 EA.
"""

import os
import sqlite3
from datetime import date

def parse_int_env(key, default):
    value_str = os.environ.get(key, str(default))
    try:
        return int(value_str)
    except ValueError:
        print(f"Warning: Invalid {key} value '{value_str}', using {default}")
        return int(default)


def parse_float_env(key, default):
    value_str = os.environ.get(key, str(default))
    try:
        return float(value_str)
    except ValueError:
        print(f"Warning: Invalid {key} value '{value_str}', using {default}")
        return float(default)


def parse_accounts_env(key, default):
    """
    Parse ACCOUNTS env var. Format: name:lot[:sell_enabled] comma-separated.
    Example: exness:0.07,hfm:0.03,ic_markets:0.02:false
    """
    value_str = os.environ.get(key)
    if not value_str:
        return default
    accounts = []
    for entry in value_str.split(','):
        parts = entry.strip().split(':')
        if len(parts) < 2:
            print(f"Warning: Invalid ACCOUNTS entry '{entry}', skipping")
            continue
        acct = {'name': parts[0], 'lot': float(parts[1])}
        if len(parts) >= 3:
            acct['sell_enabled'] = parts[2].lower() not in ('false', '0', 'no')
        accounts.append(acct)
    return accounts


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
        'lower_2': sma - (2 * std_dev),
    }


def calculate_center_price(previous_close, adjustment_pct, upper_2, lower_2):
    center = previous_close * (1 + adjustment_pct / 100)
    return max(lower_2, min(upper_2, center))


def write_set_file(filepath, lot_size, center_price, sell_range_pips, buy_range_pips,
                   sell_enabled=True, use_take_profit=True, magic_number=8001):
    content = f"""; === Basic Settings ===
UseTakeProfit={'true' if use_take_profit else 'false'}
LotSize={lot_size}
MagicNumber={magic_number}
GridCenterPrice={center_price:.2f}
; === Sell Grid Settings ===
SellEnabled={'true' if sell_enabled else 'false'}
SellRangePips={sell_range_pips}
; === Buy Grid Settings ===
BuyEnabled=true
BuyRangePips={buy_range_pips}
"""
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Written: {filepath}")


_DEFAULT_ACCOUNTS = [
    {'name': 'exness',     'lot': 0.07},
    {'name': 'hfm',        'lot': 0.03},
    {'name': 'ic_markets', 'lot': 0.02, 'sell_enabled': False},
]


def write_account_sets(accounts, magic, filename, center, sell_pips, buy_pips,
                       sell_enabled=True, use_take_profit=True):
    for acct in accounts:
        effective_sell = sell_enabled and acct.get('sell_enabled', True)
        write_set_file(
            f"/data/output/sets/{acct['name']}/{filename}.set",
            acct['lot'], center, sell_pips, buy_pips,
            effective_sell, use_take_profit, magic
        )


def main():
    conn = sqlite3.connect('/data/db/usdjpy.db')

    magic_main = parse_int_env('MAGIC_MAIN', 8001)
    accounts = parse_accounts_env('ACCOUNTS', _DEFAULT_ACCOUNTS)
    adjustment = parse_float_env('GRID_CENTER_ADJUSTMENT', 0)
    range_percent = parse_float_env('GRID_RANGE', 1)
    center_price_max_str = os.environ.get('GRID_CENTER_MAX')
    center_price_max = float(center_price_max_str) if center_price_max_str else None
    center_price_min_str = os.environ.get('GRID_CENTER_MIN')
    center_price_min = float(center_price_min_str) if center_price_min_str else None

    for acct in accounts:
        os.makedirs(f"/data/output/sets/{acct['name']}", exist_ok=True)

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
        if center_price_max is not None:
            center_price = min(center_price, center_price_max)
        if center_price_min is not None:
            center_price = max(center_price, center_price_min)

        adjustment_price = center_price - previous_close
        adjustment_pips = round(adjustment_price * 100)
        base_pips = round(previous_close * range_percent)
        sell_range_pips = base_pips - adjustment_pips
        buy_range_pips = base_pips + adjustment_pips
        rounded_center = round_to_2_or_7(center_price)

        print(f"Date: {previous_date}")
        print(f"Previous Close: {previous_close:.2f}")
        print(f"GridCenterPrice: {rounded_center:.2f}")
        print(f"SellRangePips: {sell_range_pips}")
        print(f"BuyRangePips: {buy_range_pips}")

        write_account_sets(accounts, magic_main, '1_main', rounded_center, sell_range_pips, buy_range_pips)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
