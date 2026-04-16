#!/usr/bin/env python3
"""
Account manager for FX trading accounts.

Tracks Deposit, Withdrawal, Closed Trade P/L, and Equity per account with date.
Data is imported from /data/input/account/data.csv.
"""

import csv
import os
import sqlite3
from datetime import datetime

DB_PATH = '/data/db/accounts.db'
CSV_PATH = '/data/input/account/data.csv'

RECORD_TYPES = ('deposit', 'withdrawal', 'closed_pnl', 'equity')


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            date TEXT NOT NULL,
            record_type TEXT NOT NULL CHECK(record_type IN ('deposit', 'withdrawal', 'closed_pnl', 'equity')),
            amount REAL NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_account_date ON account_records(account, date)')
    conn.commit()


# --- Subcommand handlers ---

def cmd_import(conn):
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV file not found: {CSV_PATH}")

    rows = []
    errors = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # line 1 is header
            account = row.get('account', '').strip()
            record_type = row.get('type', '').strip()
            date_raw = row.get('date', '').strip()
            amount_raw = row.get('amount', '').strip()
            note = row.get('note', '').strip() or None

            if not account:
                errors.append(f"Line {i}: 'account' is empty")
                continue
            if record_type not in RECORD_TYPES:
                errors.append(f"Line {i}: invalid type '{record_type}' (must be one of {', '.join(RECORD_TYPES)})")
                continue
            try:
                date = datetime.strptime(date_raw, '%Y.%m.%d').strftime('%Y-%m-%d')
            except ValueError:
                errors.append(f"Line {i}: invalid date '{date_raw}' (use YYYY.MM.DD)")
                continue
            try:
                amount = float(amount_raw)
            except ValueError:
                errors.append(f"Line {i}: invalid amount '{amount_raw}'")
                continue

            if record_type == 'withdrawal':
                amount = -abs(amount)

            rows.append((account, record_type, date, amount, note))

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  {e}")
        raise SystemExit("Import aborted.")

    now = datetime.now().isoformat()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM account_records')

    for account, record_type, date, amount, note in rows:
        cursor.execute(
            '''INSERT INTO account_records (account, date, record_type, amount, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (account, date, record_type, amount, note, now)
        )

    accounts = sorted({r[0] for r in rows})
    conn.commit()
    print(f"Imported {len(rows)} records for {len(accounts)} account(s): {', '.join(accounts)}")


def main():
    conn = get_conn()
    try:
        create_tables(conn)
        cmd_import(conn)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
