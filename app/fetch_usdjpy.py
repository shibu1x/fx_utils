#!/usr/bin/env python3
"""
Fetch USD/JPY hourly OHLC data using yfinance and create daily aggregates.
Daily aggregation is based on FX trading day (17:00 to next day 16:59 NY time).
"""

import os
import yfinance as yf
import sqlite3
import pandas as pd
import argparse
from datetime import datetime, timedelta


def create_tables(conn):
    """Create tables for storing USD/JPY hourly and daily OHLC data."""
    cursor = conn.cursor()

    # Hourly data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usdjpy_hourly (
            timestamp TEXT PRIMARY KEY,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER,
            created_at TEXT NOT NULL
        )
    ''')

    # Daily data table (aggregated from hourly data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usdjpy_daily (
            date TEXT PRIMARY KEY,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER,
            created_at TEXT NOT NULL
        )
    ''')

    conn.commit()


def assign_trading_day(df):
    """
    Assign trading day to each hourly record.
    Trading day runs from 17:00 to next day 16:59.

    Args:
        df: pandas DataFrame with DatetimeIndex

    Returns:
        pandas DataFrame with 'trading_day' column added
    """
    def get_trading_day(timestamp):
        # If time is 17:00 or later, assign to next day
        if timestamp.hour >= 17:
            return (timestamp.date() + timedelta(days=1)).strftime('%Y-%m-%d')
        # If time is before 17:00, assign to same day
        else:
            return timestamp.date().strftime('%Y-%m-%d')

    df['trading_day'] = df.index.map(get_trading_day)
    return df


def aggregate_daily_data(hourly_df):
    """
    Aggregate hourly data to daily data based on trading day.
    Trading day runs from 17:00 to next day 16:59.

    Args:
        hourly_df: pandas DataFrame with hourly OHLC data and 'trading_day' column

    Returns:
        pandas DataFrame with daily OHLC data
    """
    daily_data = []

    for trading_day, group in hourly_df.groupby('trading_day'):
        # Sort by timestamp to ensure correct order
        group = group.sort_index()

        daily_record = {
            'date': trading_day,
            'open': group.iloc[0]['Open'],
            'high': group['High'].max(),
            'low': group['Low'].min(),
            'close': group.iloc[-1]['Close'],
            'volume': group['Volume'].sum()
        }
        daily_data.append(daily_record)

    return pd.DataFrame(daily_data).set_index('date').sort_index()


def fetch_usdjpy_hourly(start=None):
    """
    Fetch USD/JPY hourly data from Yahoo Finance.

    Args:
        start: Start date (YYYY-MM-DD format), optional
        Note: Yahoo Finance limits intraday data to ~730 days

    Returns:
        pandas DataFrame with hourly OHLC data
    """
    ticker = yf.Ticker("JPY=X")

    # Fetch hourly data with or without start date
    if start:
        data = ticker.history(start=start, interval='1h')
    else:
        data = ticker.history(interval='1h')

    # Ensure index is timezone-aware (America/New_York)
    if data.index.tz is None:
        data.index = data.index.tz_localize('America/New_York')
    else:
        data.index = data.index.tz_convert('America/New_York')

    return data


def save_hourly_to_sqlite(data, conn, created_at):
    """
    Save hourly OHLC data to SQLite database.

    Args:
        data: pandas DataFrame with hourly OHLC data
        conn: SQLite connection
        created_at: timestamp string
    """
    cursor = conn.cursor()

    for index, row in data.iterrows():
        timestamp_str = index.isoformat()

        cursor.execute('''
            INSERT OR REPLACE INTO usdjpy_hourly
            (timestamp, open, high, low, close, volume, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp_str,
            float(row['Open']),
            float(row['High']),
            float(row['Low']),
            float(row['Close']),
            int(row['Volume']) if row['Volume'] > 0 else 0,
            created_at
        ))

    conn.commit()
    print(f"Successfully saved {len(data)} hourly records")


def save_daily_to_sqlite(data, conn, created_at):
    """
    Save daily OHLC data to SQLite database.

    Args:
        data: pandas DataFrame with daily OHLC data
        conn: SQLite connection
        created_at: timestamp string
    """
    cursor = conn.cursor()

    for date_str, row in data.iterrows():
        cursor.execute('''
            INSERT OR REPLACE INTO usdjpy_daily
            (date, open, high, low, close, volume, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            date_str,
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            int(row['volume']) if row['volume'] > 0 else 0,
            created_at
        ))

    conn.commit()
    print(f"Successfully saved {len(data)} daily records")


def main():
    """Main function to fetch hourly data and create daily aggregates."""
    parser = argparse.ArgumentParser(description='Fetch USD/JPY hourly OHLC data from Yahoo Finance')
    parser.add_argument('--start', type=str, help='Start date for data fetch (YYYY-MM-DD format)')
    args = parser.parse_args()

    if args.start:
        print(f"Fetching USD/JPY hourly data from Yahoo Finance (from {args.start})...")
    else:
        print("Fetching USD/JPY hourly data from Yahoo Finance (all available data)...")

    # Fetch hourly data
    hourly_data = fetch_usdjpy_hourly(start=args.start)

    print(f"Retrieved {len(hourly_data)} hourly records")
    print(f"Date range: {hourly_data.index[0]} to {hourly_data.index[-1]}")

    # Assign trading days
    print("\nAssigning trading days based on timestamp date...")
    hourly_data = assign_trading_day(hourly_data)

    # Aggregate to daily data
    print("Aggregating hourly data to daily...")
    daily_data = aggregate_daily_data(hourly_data)
    print(f"Created {len(daily_data)} daily records")

    # Save to SQLite
    print("\nSaving to database...")
    os.makedirs('/data/db', exist_ok=True)
    conn = sqlite3.connect('/data/db/usdjpy.db')

    try:
        create_tables(conn)
        created_at = datetime.now().isoformat()

        save_hourly_to_sqlite(hourly_data, conn, created_at)
        save_daily_to_sqlite(daily_data, conn, created_at)

    finally:
        conn.close()

    print("\nDone!")


if __name__ == '__main__':
    main()
