#!/usr/bin/env python3
"""Import account records from /data/input/account/data.tsv into SQLite."""

import csv
import os
import sqlite3
from datetime import datetime

DB_PATH = '/data/db/accounts.db'
TSV_PATH = '/data/input/account/data.tsv'

RECORD_TYPES = ('profit', 'equity', 'deposit')


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS account_records')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            record_type TEXT NOT NULL CHECK(record_type IN ('profit', 'equity', 'deposit')),
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_account_date ON account_records(account, date)')
    conn.commit()


def cmd_import(conn):
    if not os.path.exists(TSV_PATH):
        raise SystemExit(f"TSV file not found: {TSV_PATH}")

    rows = []
    errors = []
    with open(TSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for i, row in enumerate(reader, start=2):
            account = row.get('account', '').strip()
            record_type = row.get('type', '').strip().lower()
            date_raw = row.get('date', '').strip()
            amount_raw = row.get('amount', '').strip().replace(',', '')
            note = row.get('note', '').strip() or None

            if not account:
                errors.append(f"Line {i}: 'account' is empty")
                continue
            if record_type not in RECORD_TYPES:
                errors.append(f"Line {i}: invalid type '{row.get('type', '').strip()}' (must be one of {', '.join(RECORD_TYPES)})")
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

            rows.append((account, record_type, date, amount, note))

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  {e}")
        raise SystemExit("Import aborted.")

    cursor = conn.cursor()
    cursor.execute('DELETE FROM account_records')
    cursor.executemany(
        'INSERT INTO account_records (account, record_type, date, amount, note) VALUES (?, ?, ?, ?, ?)',
        rows
    )
    conn.commit()

    accounts = sorted({r[0] for r in rows})
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
