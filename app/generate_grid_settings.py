#!/usr/bin/env python3
"""
Generate grid settings .set files for MT4/MT5 EA.
Supports multiple FX pairs (USD/JPY, AUD/JPY, AUD/USD) from fx_daily.db.
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


def is_jpy_pair(pair):
    return pair.upper().endswith('JPY')


def round_to_5pip(pips):
    """Round down to nearest 5-pip boundary (offset +2)."""
    q = pips // 5
    return q * 5 + 2


def round_to_4pip(pips):
    """Round down to nearest valid value: ones digit in {1,5,9} when tens is even, {3,7} when tens is odd."""
    return (pips - 1) // 4 * 4 + 1


def pips_to_price(pips, pair):
    if is_jpy_pair(pair):
        return pips / 100
    return pips / 10000


def round_center_price(pips, grid_step_pips):
    if grid_step_pips == 5:
        return round_to_5pip(pips)
    if grid_step_pips == 4:
        return round_to_4pip(pips)
    return pips


def format_center_price(price, pair):
    if is_jpy_pair(pair):
        return f"{price:.2f}"
    return f"{price:.4f}"


def price_to_pips(price_delta, pair):
    """Convert price delta to pips."""
    if is_jpy_pair(pair):
        return round(price_delta * 100)
    return round(price_delta * 10000)


def fetch_previous_close(conn, pair):
    today = date.today().isoformat()
    cursor = conn.execute(
        "SELECT date, close FROM fx_daily WHERE pair = ? AND date < ? ORDER BY date DESC LIMIT 1",
        (pair, today)
    )
    return cursor.fetchone()


def write_set_file(filepath, lot_size, center_price, sell_range_pips, buy_range_pips,
                   pair, sell_enabled=True, use_take_profit=True, magic_number=8001, grid_step_pips=5):
    content = f"""; === Basic Settings ===
GridStepPips={grid_step_pips}
UseTakeProfit={'true' if use_take_profit else 'false'}
UseStopOrders=false
LotSize={lot_size}
MagicNumber={magic_number}
GridCenterPrice={format_center_price(center_price, pair)}
; === Sell Grid Settings ===
SellEnabled={'true' if sell_enabled else 'false'}
SellRangePips={sell_range_pips}
; === Buy Grid Settings ===
BuyEnabled=true
BuyRangePips={buy_range_pips}
"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Written: {filepath}")


def get_accounts_for_pair(pair):
    return parse_accounts_env(f'{pair}_ACCOUNTS', [])


def process_pair(conn, pair):
    row = fetch_previous_close(conn, pair)
    if not row:
        print(f"Error: No data for {pair}")
        return

    previous_date, previous_close = row

    magic = parse_int_env(f'{pair}_MAGIC_NUMBER', 8001)
    grid_step_pips = parse_int_env(f'{pair}_GRID_STEP_PIPS', 5)
    adjustment = parse_float_env(f'{pair}_GRID_CENTER_ADJUSTMENT', 0)
    range_percent = parse_float_env(f'{pair}_GRID_RANGE', 1)

    previous_close_pips = price_to_pips(previous_close, pair)
    center_pips = price_to_pips(previous_close * (1 + adjustment / 100), pair)

    base_pips = price_to_pips(previous_close * range_percent / 100, pair)

    center_max_str = os.environ.get(f'{pair}_GRID_CENTER_MAX')
    center_min_str = os.environ.get(f'{pair}_GRID_CENTER_MIN')
    if center_max_str:
        center_max_pips = price_to_pips(float(center_max_str), pair)
        if previous_close_pips - base_pips <= center_max_pips:
            center_pips = min(center_pips, center_max_pips)
    if center_min_str:
        center_min_pips = price_to_pips(float(center_min_str), pair)
        if previous_close_pips + base_pips >= center_min_pips:
            center_pips = max(center_pips, center_min_pips)

    adjustment_pips = center_pips - previous_close_pips
    sell_range_pips = base_pips - adjustment_pips
    buy_range_pips = base_pips + adjustment_pips
    rounded_center = pips_to_price(round_center_price(center_pips, grid_step_pips), pair)

    accounts = get_accounts_for_pair(pair)

    print(f"\n[{pair}]")
    print(f"Date: {previous_date}")
    print(f"Previous Close: {format_center_price(previous_close, pair)}")
    print(f"GridCenterPrice: {format_center_price(rounded_center, pair)}")
    print(f"SellRangePips: {sell_range_pips}")
    print(f"BuyRangePips: {buy_range_pips}")

    filename = pair.lower()
    for acct in accounts:
        effective_sell = acct.get('sell_enabled', True)
        write_set_file(
            f"/data/output/sets/{acct['name']}/{filename}.set",
            acct['lot'], rounded_center, sell_range_pips, buy_range_pips,
            pair, effective_sell, True, magic, grid_step_pips
        )


def main():
    conn = sqlite3.connect('/data/db/fx_daily.db')

    pairs_str = os.environ.get('PAIRS')
    if not pairs_str:
        print("Error: PAIRS environment variable is not set")
        return
    pairs = [p.strip().upper() for p in pairs_str.split(',') if p.strip()]

    for pair in pairs:
        for acct in get_accounts_for_pair(pair):
            os.makedirs(f"/data/output/sets/{acct['name']}", exist_ok=True)

    try:
        for pair in pairs:
            process_pair(conn, pair)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
