#!/usr/bin/env python3
"""
Analyze daily high/low % change from open price for FX pairs.
"""

import argparse
import os
import sqlite3


def fetch_data(conn, pairs, start, end):
    query = "SELECT pair, date, open, high, low FROM price_history WHERE 1=1"
    params = []
    if pairs:
        placeholders = ",".join("?" * len(pairs))
        query += f" AND pair IN ({placeholders})"
        params.extend(pairs)
    if start:
        query += " AND date >= ?"
        params.append(start)
    if end:
        query += " AND date <= ?"
        params.append(end)
    query += " ORDER BY pair, date"
    return conn.execute(query, params).fetchall()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze daily high/low % change from open price"
    )
    parser.add_argument("--pair", nargs="*", metavar="PAIR", help="Filter by pair (e.g. USDJPY AUDJPY)")
    parser.add_argument("--start", metavar="YYYY-MM-DD", help="Start date")
    parser.add_argument("--end", metavar="YYYY-MM-DD", help="End date")
    args = parser.parse_args()

    pairs = [p.upper() for p in args.pair] if args.pair else []

    conn = sqlite3.connect("/data/db/fx_utils.db")
    try:
        rows = fetch_data(conn, pairs, args.start, args.end)
    finally:
        conn.close()

    if not rows:
        print("No data found.")
        return

    output_path = "/data/output/daily_range_analysis.tsv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        f.write("pair\tdate\topen\thigh\tlow\thigh%\tlow%\n")
        for pair, date, open_, high, low in rows:
            high_pct = (high - open_) / open_ * 100
            low_pct = (low - open_) / open_ * 100
            f.write(f"{pair}\t{date}\t{open_}\t{high}\t{low}\t{high_pct:.3f}\t{low_pct:.3f}\n")

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
