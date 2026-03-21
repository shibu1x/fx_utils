#!/usr/bin/env python3
"""
Fetch USD/JPY price data and send Bollinger Bands to Discord.
Includes previous day's close and Bollinger Bands (1 sigma and 2 sigma).
"""

import json
import os
import sqlite3
import urllib.request
from datetime import date


def round_to_2_or_7(value):
    """
    Round value to 2 decimal places where the second decimal is 2 or 7.

    Candidates: .02, .07, .12, .17, .22, .27, ...
    Rounds to the nearest candidate.

    Args:
        value: float value to round

    Returns:
        float: rounded value
    """
    cents = round(value * 100)
    q = cents // 5
    new_cents = q * 5 + 2
    return new_cents / 100


def send_to_discord(message):
    """
    Send message to Discord via webhook.

    Args:
        message: Message to send

    Returns:
        bool: True if successful, False otherwise
    """
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set")
        return False

    payload = json.dumps({'content': message}).encode('utf-8')

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'FXUtils/1.0',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 204
    except urllib.error.URLError as e:
        print(f"Error: Failed to send Discord message: {e}")
        return False


def fetch_recent_closes(conn, days=20):
    """
    Fetch recent close prices from database.

    Args:
        conn: SQLite connection
        days: Number of days to fetch

    Returns:
        list: List of (date, close) tuples, ordered by date descending
    """
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
    """
    Calculate Bollinger Bands from close prices.

    Args:
        closes: List of close prices (most recent first)
        period: SMA period (default 20)

    Returns:
        dict: Dictionary with sma, upper/lower bands for 1σ and 2σ,
              or None if insufficient data
    """
    if len(closes) < period:
        return None

    # Use the most recent 'period' closes
    prices = closes[:period]

    # Calculate SMA
    sma = sum(prices) / period

    # Calculate standard deviation
    variance = sum((p - sma) ** 2 for p in prices) / period
    std_dev = variance ** 0.5

    # Calculate bands
    return {
        'sma': sma,
        'upper_2': sma + (2 * std_dev),
        'upper_1': sma + (1 * std_dev),
        'lower_1': sma - (1 * std_dev),
        'lower_2': sma - (2 * std_dev),
    }


def main():
    """Main function to fetch prices and send to Discord."""
    conn = sqlite3.connect('data/db/usdjpy.db')

    try:
        # Fetch recent close prices
        rows = fetch_recent_closes(conn, days=20)

        if not rows:
            print("Error: No data available")
            return

        # Previous day's close
        previous_date = rows[0][0]
        previous_close = rows[0][1]

        # Extract close prices for Bollinger Bands calculation
        closes = [row[1] for row in rows]

        # Calculate Bollinger Bands
        bands = calculate_bollinger_bands(closes)

        # Round prices to 2 or 7
        rounded_close = round_to_2_or_7(previous_close)

        # Build message
        if bands is not None:
            rounded_upper_2 = round_to_2_or_7(bands['upper_2'])
            rounded_upper_1 = round_to_2_or_7(bands['upper_1'])
            rounded_sma = round_to_2_or_7(bands['sma'])
            rounded_lower_1 = round_to_2_or_7(bands['lower_1'])
            rounded_lower_2 = round_to_2_or_7(bands['lower_2'])

            # Build band lines in descending order with Close in correct position
            band_items = [
                ('Upper 2σ', rounded_upper_2, bands['upper_2']),
                ('Upper 1σ', rounded_upper_1, bands['upper_1']),
                ('SMA', rounded_sma, bands['sma']),
                ('Lower 1σ', rounded_lower_1, bands['lower_1']),
                ('Lower 2σ', rounded_lower_2, bands['lower_2']),
            ]

            band_lines = []
            close_added = False

            for label, rounded_val, raw_val in band_items:
                # Insert Close before this band if Close is above it
                if not close_added and previous_close > raw_val:
                    band_lines.append(f"  Close:    {rounded_close:.2f}")
                    close_added = True
                band_lines.append(f"  {label + ':':<10s}{rounded_val:.2f}")

            # Close is below all bands
            if not close_added:
                band_lines.append(f"  Close:    {rounded_close:.2f}")

            lines = [
                f"**USD/JPY Daily Report** ({previous_date})",
                f"",
                f"**Bollinger Bands (20, 1σ/2σ)**",
            ] + band_lines
        else:
            lines = [
                f"**USD/JPY Daily Report** ({previous_date})",
                f"",
                f"Bollinger Bands: Insufficient data",
            ]

        message = "\n".join(lines)

        # Send to Discord
        if send_to_discord(message):
            print(f"Sent to Discord:\n{message}")
        else:
            print(f"Failed to send:\n{message}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
