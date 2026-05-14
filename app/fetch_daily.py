#!/usr/bin/env python3
"""
Fetch daily OHLC data for multiple FX pairs (USD/JPY, AUD/USD) using yfinance.
"""

import os
import yfinance as yf
import sqlite3
import argparse
from datetime import datetime, timedelta

PAIRS = {
    "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X",
    "AUDJPY": "AUDJPY=X",
}


def create_table(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS fx_daily (
            pair TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (pair, date)
        )
    ''')
    conn.commit()


def fetch_daily(ticker_symbol, start=None):
    ticker = yf.Ticker(ticker_symbol)
    if start is None:
        start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    data = ticker.history(start=start, interval="1d")
    return data


def save_to_sqlite(pair, data, conn, created_at):
    cursor = conn.cursor()
    for index, row in data.iterrows():
        date_str = index.strftime("%Y-%m-%d")
        cursor.execute('''
            INSERT OR REPLACE INTO fx_daily
            (pair, date, open, high, low, close, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            pair,
            date_str,
            float(row["Open"]),
            float(row["High"]),
            float(row["Low"]),
            float(row["Close"]),
            created_at,
        ))
    conn.commit()
    print(f"  Saved {len(data)} records")


def main():
    parser = argparse.ArgumentParser(description="Fetch daily FX OHLC data from Yahoo Finance")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    args = parser.parse_args()

    os.makedirs("/data/db", exist_ok=True)
    conn = sqlite3.connect("/data/db/fx_daily.db")

    try:
        create_table(conn)
        created_at = datetime.now().isoformat()

        for pair in PAIRS:
            ticker_symbol = PAIRS[pair]
            print(f"Fetching {pair} ({ticker_symbol})...")
            data = fetch_daily(ticker_symbol, start=args.start)
            if data.empty:
                print(f"  No data returned")
                continue
            print(f"  {len(data)} records: {data.index[0].date()} to {data.index[-1].date()}")
            save_to_sqlite(pair, data, conn, created_at)

    finally:
        conn.close()

    print("Done!")


if __name__ == "__main__":
    main()
