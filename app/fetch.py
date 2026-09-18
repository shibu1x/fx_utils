#!/usr/bin/env python3
"""
Fetch daily close price for multiple FX pairs (USD/JPY, AUD/USD, NZD/USD, GBP/USD) using yfinance.
"""

import argparse
import math
import os
import sqlite3
from datetime import datetime, timedelta

import yfinance as yf

PAIRS = {
    "USDJPY": "JPY=X",
}


def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            pair TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            PRIMARY KEY (pair, date)
        )
    """)
    conn.commit()


def fetch_daily(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    data = ticker.history(start=start, interval="1d")
    return data


def truncate(value, decimals):
    factor = 10 ** decimals
    return math.floor(value * factor) / factor


def save_to_sqlite(pair, data, conn):
    decimals = 3 if "JPY" in pair else 5
    cursor = conn.cursor()
    for index, row in data.iterrows():
        date_str = index.strftime("%Y-%m-%d")
        cursor.execute(
            """
            INSERT OR REPLACE INTO price_history
            (pair, date, open, high, low, close)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                pair,
                date_str,
                truncate(float(row["Open"]), decimals),
                truncate(float(row["High"]), decimals),
                truncate(float(row["Low"]), decimals),
                truncate(float(row["Close"]), decimals),
            ),
        )
    conn.commit()
    print(f"  Saved {len(data)} records")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch daily FX OHLC data from Yahoo Finance"
    )
    parser.add_argument(
        "pairs",
        nargs="*",
        metavar="PAIR",
        help=f"Pairs to fetch (default: {', '.join(PAIRS.keys())}). Any pair is accepted (e.g. AUDJPY).",
    )
    args = parser.parse_args()

    if args.pairs:
        target_pairs = {p.upper(): PAIRS.get(p.upper(), f"{p.upper()}=X") for p in args.pairs}
    else:
        target_pairs = PAIRS

    os.makedirs("/data/db", exist_ok=True)
    conn = sqlite3.connect("/data/db/fx_utils.db")

    try:
        create_table(conn)

        for pair, ticker_symbol in target_pairs.items():
            print(f"Fetching {pair} ({ticker_symbol})...")
            data = fetch_daily(ticker_symbol)
            if data.empty:
                print(f"  No data returned")
                continue
            print(
                f"  {len(data)} records: {data.index[0].date()} to {data.index[-1].date()}"
            )
            save_to_sqlite(pair, data, conn)

    finally:
        conn.close()

    print("Done!")


if __name__ == "__main__":
    main()
